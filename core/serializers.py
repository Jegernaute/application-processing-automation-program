from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.models import StudentCode, LecturerCode, ManagerCode, Request
from django.core.mail import send_mail
from rest_framework.authtoken.models import Token
import uuid
import re
import random

# Отримуємо кастомну модель користувача
User = get_user_model()

# СЕРІАЛІЗАТОР ДЛЯ ПЕРЕВІРКИ КОДУ (без створення користувача)
class VerifyCodeSerializer(serializers.Serializer):
    code = serializers.CharField()  # Очікуємо код (наприклад, ST12345)

    def validate_code(self, value):
        # Очищаємо дані перед перевіркою
        self.role = None
        self.profile_data = {}

        # Перевіряємо, чи код належить студенту
        student = StudentCode.objects.filter(code=value).first()
        if student:
            self.role = 'student'
            self.profile_data = {
                "first_name": student.first_name,
                "last_name": student.last_name,
                "patronymic": student.patronymic,
            }
        else:
            # Перевіряємо, чи код належить викладачу
            lecturer = LecturerCode.objects.filter(code=value).first()
            if lecturer:
                self.role = 'lecturer'
                self.profile_data = {
                    "first_name": lecturer.first_name,
                    "last_name": lecturer.last_name,
                    "patronymic": lecturer.patronymic,
                }
            else:
                # Перевіряємо, чи код належить менеджеру
                manager = ManagerCode.objects.filter(code=value).first()
                if manager:
                    self.role = 'manager'
                    self.profile_data = {
                        "first_name": manager.first_name,
                        "last_name": manager.last_name,
                        "patronymic": manager.patronymic,
                    }
                else:
                    # Якщо код не знайдено взагалі — помилка
                    raise serializers.ValidationError("Код не знайдено або недійсний.")

        return value


# СЕРІАЛІЗАТОР ДЛЯ РЕЄСТРАЦІЇ КОРИСТУВАЧА
class RegisterSerializer(serializers.Serializer):
    code = serializers.CharField()              # Код реєстрації (student, lecturer, manager)
    email = serializers.EmailField()            # Email користувача
    phone = serializers.CharField()             # Номер телефону
    password = serializers.CharField(required=False, allow_blank=True)  # Пароль (не обов'язковий)

    def validate(self, data):
        # Витягуємо вхідні дані
        code = data.get('code')
        email = data.get('email')
        phone = normalize_phone(data.get('phone'))  # Нормалізуємо номер телефону

        # Перевірка унікальності email
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "Користувач із цією поштою вже існує."})

        # Початкові змінні
        role = None
        profile_data = {}

        # Перевіряємо тип коду (student / lecturer / manager)
        student = StudentCode.objects.filter(code=code).first()
        if student:
            role = 'student'
            profile_data = {
                "first_name": student.first_name,
                "last_name": student.last_name,
                "patronymic": student.patronymic,
            }
        else:
            lecturer = LecturerCode.objects.filter(code=code).first()
            if lecturer:
                role = 'lecturer'
                profile_data = {
                    "first_name": lecturer.first_name,
                    "last_name": lecturer.last_name,
                    "patronymic": lecturer.patronymic,
                }
            else:
                manager = ManagerCode.objects.filter(code=code).first()
                if manager:
                    role = 'manager'
                    profile_data = {
                        "first_name": manager.first_name,
                        "last_name": manager.last_name,
                        "patronymic": manager.patronymic,
                    }
                else:
                    raise serializers.ValidationError({"code": "Код не знайдено або недійсний."})

        # Додаємо оброблені значення до validated_data
        data['role'] = role
        data['profile_data'] = profile_data
        data['phone'] = phone  # зберігаємо нормалізований номер

        return data

    def create(self, validated_data):
        # Витягуємо значення
        role = validated_data['role']
        profile_data = validated_data['profile_data']
        password = validated_data.get('password')

        # Якщо пароль не надано — створюємо службовий випадковий
        if not password:
            password = uuid.uuid4().hex

        # Створюємо користувача через кастомний менеджер
        user = User.objects.create_user(
            email=validated_data['email'],
            phone=validated_data['phone'],
            password=password,
            role=role,
            **profile_data  # Розпаковуємо first_name, last_name, patronymic
        )

        # Активуємо акаунт
        user.is_active = True

        # Якщо менеджер — надаємо доступ до адмінки
        if role == 'manager':
            user.is_staff = True

        # Закладка на майбутню перевірку email
        # user.is_email_confirmed = False

        user.save()

        # Пробуємо надіслати лист підтвердження/вітання
        try:
            send_mail(
                subject="Дякуємо за реєстрацію!",
                message="Ваша реєстрація пройшла успішно. Якщо це були не ви — проігноруйте цей лист.",
                from_email="noreply@example.com",
                recipient_list=[user.email],
                fail_silently=True,  # Якщо помилка — не зупиняти виконання
            )
        except Exception:
            pass  # Можна логувати помилку, якщо потрібно

        return user





# 🔧 ФУНКЦІЯ НОРМАЛІЗАЦІЇ НОМЕРА ТЕЛЕФОНУ
def normalize_phone(phone: str) -> str:
    # Видаляє всі символи, крім цифр і плюса ("+")
    phone = re.sub(r"[^\d+]", "", phone)

    # Якщо номер починається з "0", замінюємо на "+380"
    if phone.startswith("0"):
        phone = "+380" + phone[1:]
    # Якщо номер починається з "380", додаємо "+"
    elif phone.startswith("380"):
        phone = "+" + phone
    # Якщо вже правильний формат — нічого не змінюємо
    elif phone.startswith("+380"):
        pass
    # Усі інші варіанти — помилка
    else:
        raise serializers.ValidationError({
            "phone": "Невірний формат телефону. Має бути у форматі +380XXXXXXXXX"
        })

    # Перевіряємо, що результат повністю відповідає шаблону +380XXXXXXXXX
    if not re.fullmatch(r"\+380\d{9}", phone):
        raise serializers.ValidationError({
            "phone": "Номер телефону має бути у форматі +380XXXXXXXXX"
        })

    return phone


# 🔐 СЕРІАЛІЗАТОР ДЛЯ ЛОГІНУ КОРИСТУВАЧА (ПО EMAIL І КОДУ)
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()     # Поле email
    code = serializers.CharField()       # Код перевірки ролі

    def validate(self, data):
        email = data.get("email")
        code = data.get("code")

        # Шукаємо користувача за email
        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError({
                "email": "Користувача з такою поштою не знайдено."
            })

        # Перевірка, чи правильний код для цієї ролі
        valid_code = False

        if user.role == 'student' and StudentCode.objects.filter(code=code).exists():
            valid_code = True
        elif user.role == 'lecturer' and LecturerCode.objects.filter(code=code).exists():
            valid_code = True
        elif user.role == 'manager' and ManagerCode.objects.filter(code=code).exists():
            valid_code = True

        # Якщо код не знайдено або не відповідає ролі — помилка
        if not valid_code:
            raise serializers.ValidationError({
                "code": "Невірний код або не відповідає ролі користувача."
            })

        # Додаємо користувача до validated_data
        data['user'] = user
        return data

    def create(self, validated_data):
        user = validated_data['user']

        # Отримуємо токен або створюємо новий (використовується для авторизації)
        token, created = Token.objects.get_or_create(user=user)

        # Повертаємо токен і базову інформацію про користувача
        return {
            "token": token.key,
            "user": {
                "email": user.email,
                "role": user.role,
                "first_name": user.first_name,
                "last_name": user.last_name
            }
        }
class RequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = [
            'id',
            'name',
            'type_request',
            'description',
            'photo',
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        request = Request.objects.create(
            user=user,
            **validated_data  # без code — модель сама згенерує
        )
        return request

class RequestDetailSerializer(serializers.ModelSerializer):
    assigned_master = serializers.SerializerMethodField()

    class Meta:
        model = Request
        fields = [
            'id',
            'name',
            'type_request',
            'description',
            'status',
            'photo',
            'created_at',
            'assigned_master',
        ]

    def get_assigned_master(self, obj):
        user = self.context['request'].user
        visible_statuses = ['in_progress', 'done']  # або ['in_progress', 'completed'], якщо використовуєш таке значення

        # Показати завжди менеджеру
        if user.role == 'manager':
            return self._get_master_block(obj)

        # Показати користувачу тільки коли заявка в дозволеному статусі
        if obj.status in visible_statuses:
            return self._get_master_block(obj)

        # Інакше не показувати
        return None

    def _get_master_block(self, obj):
        return {
            "name": obj.assigned_master_name,
            "company": obj.assigned_master_company,
            "phone": obj.assigned_master_phone,
            "company_phone": obj.assigned_company_phone
        }