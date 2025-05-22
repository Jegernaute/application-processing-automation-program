from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from core.serializers import RegisterSerializer
from core.serializers import VerifyCodeSerializer
from core.serializers import LoginSerializer
from core.serializers import RequestCreateSerializer
from core.models import Request

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
    permission_classes = [IsAuthenticated]

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