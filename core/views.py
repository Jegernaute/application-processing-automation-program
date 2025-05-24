from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from core.serializers import RequestCreateSerializer,RequestDetailSerializer,LoginSerializer,VerifyCodeSerializer,RegisterSerializer
from core.models import Request
from core.permissions import IsStudentOrLecturer,IsManager
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.exceptions import PermissionDenied



# 🔍 Ендпоінт для перевірки реєстраційного коду (без створення користувача)
class VerifyCodeView(APIView):
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
        if user.role == 'manager':
            return Request.objects.all()
        return Request.objects.filter(user=user)

class RequestUpdateView(RetrieveUpdateAPIView):
    queryset = Request.objects.all()
    serializer_class = RequestDetailSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        request = self.request
        user = request.user
        instance = self.get_object()

        # Менеджер може оновлювати будь-які поля
        if user.role == 'manager':
            serializer.save()
            return

        # Студент або викладач — лише свої заявки в статусі 'empty' або 'pending'
        if instance.user != user:
            raise PermissionDenied("Це не ваша заявка.")
        if instance.status not in ['empty', 'pending']:
            raise PermissionDenied("Редагувати можна лише в статусі 'empty' або 'pending'.")

        # Заборонені поля
        for field in ['assigned_master_name', 'assigned_master_company', 'assigned_master_phone', 'assigned_company_phone', 'status']:
            if field in serializer.validated_data:
                raise PermissionDenied(f"Недозволено змінювати поле {field}.")

        serializer.save()