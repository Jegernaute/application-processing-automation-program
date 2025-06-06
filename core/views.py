from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import ListAPIView, get_object_or_404, CreateAPIView, DestroyAPIView
from core.serializers import RequestCreateSerializer, RequestDetailSerializer, LoginSerializer, VerifyCodeSerializer, \
    RegisterSerializer, RequestImageSerializer, UserProfileSerializer
from core.models import Request, RequestImage, User
from core.permissions import IsStudentOrLecturer, IsManager, IsOwnerOrManager, IsOwner
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from core.services.request_status import can_set_done
from core.services.notifications import (
    send_status_email,
    render_request_completed_message,
    render_request_rejected_message,
    render_request_approved_message,
    render_request_restored_message, render_master_assigned_message, render_user_confirmed_message
)
from django.db.models import Q



# 🔍 Ендпоінт для перевірки реєстраційного коду (без створення користувача)
class VerifyCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Прив'язуємо дані запиту до VerifyCodeSerializer
        serializer = VerifyCodeSerializer(data=request.data)

        # Якщо код валідний
        if serializer.is_valid():
            return Response({
                "status": "valid",                    # Повертаємо, що код дійсний
                "role": serializer.role,              # Роль, визначена за кодом
                **serializer.profile_data             # Ім’я, прізвище, по-батькові
            }, status=status.HTTP_200_OK)

        # Якщо код невірний або не знайдено — повертаємо помилку
        return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)


#  Ендпоінт для реєстрації нового користувача
class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Передаємо POST-дані у RegisterSerializer
        serializer = RegisterSerializer(data=request.data)

        # Якщо дані валідні (код знайдено, email унікальний, номер правильний)
        if serializer.is_valid():
            # Створюємо користувача через create()
            user = serializer.save()
            return Response({
                "message": "Користувача зареєстровано успішно.",
                "email": user.email,
                "role": user.role
            }, status=status.HTTP_201_CREATED)

        # Якщо були помилки — повертаємо помилку з поясненням
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  Ендпоінт для входу користувача (автентифікація)
class LoginUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Передаємо email та code у LoginSerializer
        serializer = LoginSerializer(data=request.data)

        # Якщо користувач і код валідні
        if serializer.is_valid():
            # Метод create() повертає токен + інфо про користувача
            result = serializer.save()
            return Response({
                "message": "Вхід успішний",
                "token": result["token"],   # Токен авторизації
                "user": result["user"]      # Дані користувача: email, ім’я, роль
            }, status=status.HTTP_200_OK)

        # Якщо помилка авторизації — невірний email або код
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

class RequestCreateView(APIView):
    permission_classes = [IsAuthenticated, IsStudentOrLecturer]

    def post(self, request):
        serializer = RequestCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            new_request = serializer.save()
            return Response({
                "message": "Заявку створено успішно",
                "code": new_request.code,
                "id": new_request.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SomeManagerOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

class RequestListView(ListAPIView):
    serializer_class = RequestDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Користувач бачить тільки свої заявки
        if user.role in ["student", "lecturer"]:
            qs = Request.objects.filter(user=user)

            # Отримуємо GET-параметри
            query = self.request.query_params.get("query")
            status_param = self.request.query_params.get("status")
            type_request = self.request.query_params.get("type_request")

            # Пошук по назві або коду
            if query:
                qs = qs.filter(Q(name__icontains=query) | Q(code__icontains=query))

            # Фільтр по статусу
            if status_param:
                qs = qs.filter(status=status_param)

            # Фільтр по типу заявки
            if type_request:
                qs = qs.filter(type_request=type_request)

            return qs

        # Менеджер бачить усі заявки, крім чернеток і відхилених
        elif user.role == "manager":
            qs = Request.objects.exclude(status__in=["empty", "rejected"])

            # Параметри фільтрації
            query = self.request.query_params.get("query")
            status_param = self.request.query_params.get("status")
            type_request = self.request.query_params.get("type_request")


         # Пошук за назвою або кодом
            if query:
                qs = qs.filter(Q(name__icontains=query) | Q(code__icontains=query))

            if status_param:
                qs = qs.filter(status=status_param)

            if type_request:
                qs = qs.filter(type_request=type_request)

            return qs

        # Якщо роль невідома або інша — повернути пустий список
        return Request.objects.none()

    def get_serializer_context(self):
        return {'request': self.request}



class RequestUpdateView(RetrieveUpdateAPIView):
    queryset = Request.objects.all()
    serializer_class = RequestDetailSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def perform_update(self, serializer):
        request = self.request
        user = request.user
        instance = self.get_object()
        validated_data = serializer.validated_data

        # -------------------------
        #  Менеджер
        # -------------------------
        if user.role == 'manager':
            master_fields = [
                "assigned_master_name",
                "assigned_master_company",
                "assigned_master_phone",
                "assigned_company_phone",
                "work_date"
            ]
            updating_master = any(field in validated_data for field in master_fields)

            # Призначення майстра → статус on_check + email
            if updating_master:
                if instance.status != 'approved':
                    raise PermissionDenied("Призначати майстра можна лише в статусі 'approved'.")
                validated_data['status'] = 'on_check'
                serializer.save()

                msg = render_master_assigned_message(instance)
                send_status_email(
                    to_email=instance.user.email,
                    subject="Майстра призначено",
                    message=msg
                )
                return

            # Завершення заявки
            if validated_data.get("status") == "done":
                can_complete, reason = can_set_done(instance)
                if not can_complete:
                    raise PermissionDenied(reason)

                validated_data['completed_at'] = timezone.now()
                msg = render_request_completed_message(instance, manager_email=user.email)
                send_status_email(
                    to_email=instance.user.email,
                    subject="Заявка завершена",
                    message=msg
                )
                serializer.save()
                return

            # Відхилення
            if validated_data.get("status") == "rejected":
                reason = request.data.get("rejection_comment", "не вказана")  # отримаємо причину з запиту
                message = (
                    f"Заявку №{instance.code} відхилено.\n"
                    f"Причина: {reason}."
                )
                send_status_email(
                    to_email=instance.user.email,
                    subject="Заявку відхилено",
                    message=message
                )

            # Схвалення
            if validated_data.get("status") == "approved":
                msg = render_request_approved_message(instance)
                send_status_email(
                    to_email=instance.user.email,
                    subject="Заявка схвалена",
                    message=msg
                )

            # Відновлення з done → approved
            old_status = instance.status
            new_status = validated_data.get("status")
            if old_status == "done" and new_status == "approved":
                msg = render_request_restored_message(instance)
                send_status_email(
                    to_email=instance.user.email,
                    subject="Заявку відновлено",
                    message=msg
                )

            serializer.save()
            return

        # -------------------------
        #  Користувач (студент або викладач)
        # -------------------------
        if user.role not in ['student', 'lecturer']:
            raise PermissionDenied("Тільки студент або викладач може редагувати свою заявку.")

        if instance.user != user:
            raise PermissionDenied("Це не ваша заявка.")

        # Заборонені поля для редагування користувачем
        forbidden_fields = [
            'assigned_master_name',
            'assigned_master_company',
            'assigned_master_phone',
            'assigned_company_phone',
            'status',
            'work_date',
        ]
        for field in forbidden_fields:
            if field in validated_data:
                raise PermissionDenied(f"Недозволено змінювати поле {field}.")

        # Редагування дозволене лише в статусах чернетки
        if instance.status == 'rejected':
            validated_data['status'] = 'empty'  # Автоматичне повернення у чернетку
        elif instance.status not in ['empty']:
            raise PermissionDenied("Редагувати можна лише в статусі 'empty' після відхилення ('rejected').")

        serializer.save()


class ConfirmRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        instance = get_object_or_404(Request, pk=pk)

        # Перевірка доступу
        if instance.user != request.user:
            raise PermissionDenied("Це не ваша заявка.")

        if instance.status != 'on_check':
            raise PermissionDenied("Підтвердити можна лише в статусі 'on_check'.")

        if instance.work_date and timezone.now() < instance.work_date:
            raise PermissionDenied("Підтвердження можливе лише після завершення запланованого часу візиту.")

        # Підтвердження
        instance.user_confirmed = True
        instance.save()
        # Повідомлення
        msg = render_user_confirmed_message(instance)
        send_status_email(
            to_email=instance.user.email,
            subject="Заявка підтверджена користувачем",
            message=msg
        )

        return Response({"message": "Заявку підтверджено"}, status=200)

class RequestImageListAPIView(ListAPIView):
    serializer_class = RequestImageSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get_queryset(self):
        request_id = self.kwargs['pk']
        request_obj = get_object_or_404(Request, pk=request_id)
        self.check_object_permissions(self.request, request_obj)
        return RequestImage.objects.filter(request=request_obj)

class RequestImageUploadAPIView(CreateAPIView):
    serializer_class = RequestImageSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def perform_create(self, serializer):
        request_id = self.kwargs['pk']
        request_obj = get_object_or_404(Request, pk=request_id)
        self.check_object_permissions(self.request, request_obj)

        # Обмеження на кількість фото (макс. 5)
        if RequestImage.objects.filter(request=request_obj).count() >= 5:
            raise PermissionDenied("Не можна прикріпити більше 5 фото до заявки.")

        serializer.save(request=request_obj)

    def post(self, request, pk):
        req = get_object_or_404(Request, pk=pk)

        # Перевірка кількості фото
        if RequestImage.objects.filter(request=req).count() >= 5:
            return Response({"error": "Можна додати максимум 5 зображень до заявки."}, status=400)

        files = request.FILES.getlist('image')

        if not files:
            return Response({"error": "Не передано файлів."}, status=400)

        if len(files) + RequestImage.objects.filter(request=req).count() > 5:
            return Response({"error": "Можна завантажити максимум 5 зображень до заявки."}, status=400)

        created = []

        for file in files:
            serializer = self.get_serializer(data={'image': file})
            serializer.is_valid(raise_exception=True)
            serializer.save(request=req)
            created.append(serializer.data)

        return Response(created, status=201)


class RequestImageDeleteAPIView(DestroyAPIView):
    queryset = RequestImage.objects.all()
    serializer_class = RequestImageSerializer
    permission_classes = [IsAuthenticated, IsOwner]  # менеджеру заборонено

    def get_object(self):
        obj = super().get_object()
        self.check_object_permissions(self.request, obj)
        return obj


class SubmitRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        # 1. Отримати заявку або 404
        request_obj = get_object_or_404(Request, pk=pk)

        # 2. Перевірка: заявка має належати користувачу
        if request_obj.user != request.user:
            raise PermissionDenied("Це не ваша заявка.")

        # 3. Перевірка статусу
        if request_obj.status != 'empty':
            return Response(
                {"detail": "Заявку вже відправлено або обробляється."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3.1 Перевірка опису
        if not request_obj.description or request_obj.description.strip() == "":
            return Response({"error": "Поле 'Опис' є обов'язковим для відправки заявки."}, status=400)

        # 3.2 Перевірка зображень
        if not request_obj.images.exists():
            return Response({"error": "Необхідно додати хоча б одне зображення до заявки."}, status=400)

        # 4. Зміна статусу
        request_obj.status = 'pending'
        request_obj.save()

        # 5. Надсилання email менеджеру
        managers = User.objects.filter(role='manager')
        for manager in managers:
            send_status_email(
                to_email=manager.email,
                subject="Нова заявка на перевірку",
                message=f"Нова заявка на перевірку: {request_obj.code} — {request_obj.name}"
            )

        # 6. Повернення відповіді
        return Response(
            {"detail": "Заявку відправлено на перевірку"},
            status=status.HTTP_200_OK
        )

class UserProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Якщо використовуєш TokenAuthentication
        if hasattr(user, 'auth_token'):
            user.auth_token.delete()

        return Response({"message": "Ви вийшли з системи"}, status=status.HTTP_200_OK)