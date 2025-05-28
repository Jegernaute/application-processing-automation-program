from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import ListAPIView, get_object_or_404, CreateAPIView, DestroyAPIView
from core.serializers import RequestCreateSerializer, RequestDetailSerializer, LoginSerializer, VerifyCodeSerializer, \
    RegisterSerializer, RequestImageSerializer
from core.models import Request, RequestImage
from core.permissions import IsStudentOrLecturer, IsManager, IsOwnerOrManager
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from core.services.request_status import can_set_done


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


# 📝 Ендпоінт для реєстрації нового користувача
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


# 🔐 Ендпоінт для входу користувача (автентифікація)
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
            return Request.objects.filter(user=user)

        # Менеджер бачить усі заявки
        queryset = Request.objects.all()

        # Якщо передано фільтр статусу — застосувати його
        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)

        return queryset

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


        # 1. Менеджер

        if user.role == 'manager':

            # Призначення майстра в статусі approved → автоматично переводимо в on_check
            master_fields = [
                "assigned_master_name",
                "assigned_master_company",
                "assigned_master_phone",
                "assigned_company_phone",
                "work_date"
            ]
            updating_master = any(field in validated_data for field in master_fields)

            if updating_master:
                if instance.status != 'approved':
                    raise PermissionDenied("Призначати майстра можна лише в статусі 'approved'.")
                validated_data['status'] = 'on_check'
                serializer.save()
                return

            # Завершення заявки
            if validated_data.get('status') == 'done':
                can_complete, reason = can_set_done(instance)
                if not can_complete:
                    raise PermissionDenied(reason)

                validated_data['completed_at'] = timezone.now()

                send_mail(
                    subject="Заявка завершена",
                    message=(
                        f"Заявка була позначена як виконана. "
                        f"Якщо у вас є питання або скарги — напишіть на пошту менеджера: {user.email} "
                        f"протягом 30 днів після завершення."
                    ),
                    from_email=user.email,
                    recipient_list=[instance.user.email],
                    fail_silently=True
                )

                serializer.save()
                return

            # Інші зміни менеджера (напр., зміна статусу) — дозволені
            serializer.save()
            return


        # 2. Студент / Викладач
        if instance.user != user:
            raise PermissionDenied("Це не ваша заявка.")
        if instance.status not in ['empty', 'pending']:
            raise PermissionDenied("Редагувати можна лише в статусі 'empty' або 'pending'.")

        # Користувач може лише підтвердити виконання
        if validated_data.get('user_confirmed') is True and instance.status == 'on_check':
            instance.user_confirmed = True
            instance.save()
            return

        # Заборонені поля для користувача
        forbidden_fields = [
            'assigned_master_name',
            'assigned_master_company',
            'assigned_master_phone',
            'assigned_company_phone',
            'status',
            'work_date'
        ]
        for field in forbidden_fields:
            if field in validated_data:
                raise PermissionDenied(f"Недозволено змінювати поле {field}.")

        serializer.save()

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

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(request=req)
        return Response(serializer.data, status=201)


class RequestImageDeleteAPIView(DestroyAPIView):
    queryset = RequestImage.objects.all()
    serializer_class = RequestImageSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get_object(self):
        obj = super().get_object()
        self.check_object_permissions(self.request, obj.request)
        return obj
