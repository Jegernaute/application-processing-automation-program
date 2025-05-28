from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.conf import settings
import random
from django.utils import timezone
from datetime import timedelta


# Менеджер користувачів для кастомної моделі User
class CustomUserManager(BaseUserManager):
    use_in_migrations = True  # Дозволяє використовувати менеджер у міграціях

    # Створення звичайного користувача
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обовʼязковий')  # Перевірка, що email заданий
        email = self.normalize_email(email)  # Нормалізує email (нижній регістр тощо)
        user = self.model(email=email, **extra_fields)  # Створює екземпляр користувача
        user.set_password(password)  # Хешує пароль
        user.save(using=self._db)  # Зберігає в базу даних
        return user

    # Створення суперкористувача
    def create_superuser(self, email, password=None, **extra_fields):
        # Примусово виставляємо прапорці для адміндоступу
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        # Перевіряємо, чи прапорці дійсно виставлені
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser повинен мати is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser повинен мати is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


# Основна модель користувача, яка замінює стандартну модель User у Django
class User(AbstractUser):
    username = None  # Вимикаємо стандартне поле username

    # Основні дані користувача
    email = models.EmailField(unique=True)  # Email стає основним логіном
    phone = models.CharField(max_length=50, blank=True)  # Номер телефону (необов'язковий)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    patronymic = models.CharField(max_length=50, blank=True)  # По-батькові (необов'язкове)

    # Вибір ролі користувача
    ROLE_CHOICES = [
        ('student', 'Студент'),
        ('lecturer', 'Викладач'),
        ('manager', 'Менеджер'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    # Вказуємо свій менеджер
    objects = CustomUserManager()

    # Поле, яке буде використовуватись для логіну
    USERNAME_FIELD = 'email'

    # Поля, обовʼязкові при створенні суперкористувача через createsuperuser
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role']

    def __str__(self):
        return f'{self.email} ({self.role})'  # Як користувач буде відображатись у Django-адмінці



# Модель заявки від користувача (на ремонт тощо)
class Request(models.Model):
    # Типи заявок
    TYPE_CHOICES = [
        ('electrical_appliances', 'Електроприлади'),
        ('electricity', 'Електрика'),
        ('plumbing', 'Сантехніка'),
        ('heating', 'Опалення'),
        ('ventilation', 'Вентиляція'),
        ('internet', 'Інтернет'),
        ('furniture', 'Меблі'),
        ('windows_doors', 'Вікна / Двері'),
        ('other', 'Інше'),
    ]

    # Стани обробки заявки
    STATUS_CHOICES = [
        ('pending', 'В обробці'),
        ('approved', 'Підтверджено'),
        ('rejected', 'Відхилено'),
        ('done', 'Виконано'),
        ('on_check', 'На перевірці'),
        ('empty', 'Чернетка'),
    ]

    name = models.CharField(max_length=255)  # Назва заявки
    type_request = models.CharField(max_length=50, choices=TYPE_CHOICES)  # Тип заявки
    description = models.TextField()  # Детальний опис проблеми
    location_unit = models.ForeignKey('LocationUnit', on_delete=models.CASCADE, null=False)
    room_number = models.CharField(max_length=20, null=True)
    entrance_number = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Дата створення
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='empty')# Статус
    code = models.CharField(max_length=4, blank=True, null=True)
    assigned_master_name = models.CharField(max_length=100, blank=True, null=True)
    assigned_master_company = models.CharField(max_length=100, blank=True, null=True)
    assigned_master_phone = models.CharField(max_length=20, blank=True, null=True)
    assigned_company_phone = models.CharField(max_length=20, blank=True, null=True)
    work_date = models.DateTimeField(null=True, blank=True)
    user_confirmed = models.BooleanField(default=False)
    manager_confirmed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requests'
    )  # Хто створив заявку

    def save(self, *args, **kwargs):
        if not self.code:
            while True:
                generated_code = str(random.randint(1000, 9999))
                if not Request.objects.filter(code=generated_code).exists():
                    self.code = generated_code
                    break

        # Перевірка переходу в статус "done" (або "completed" — залежить від поля)
        if self.status == 'done' and self.completed_at is None:
            self.completed_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_type_request_display()}) - {self.status}"
        # Повертає тип заявки та статус у зручному вигляді



# Модель студентського коду для попередньої перевірки під час реєстрації
class StudentCode(models.Model):
    # Вибір факультету (для автоматичного заповнення)
    FACULTY_CHOICES = [
        # Кожен варіант дублюється в парі (ключ = відображення)
        ('Автомобілів', 'Автомобілів'),
        ('Виробництва, ремонту та матеріалознавства', 'Виробництва, ремонту та матеріалознавства'),
        ('Вищої математики', 'Вищої математики'),
        ('Двигунів і теплотехніки', 'Двигунів і теплотехніки'),
        ('Дорожньо-будівельних матеріалів і хімії', 'Дорожньо-будівельних матеріалів і хімії'),
        ('Екології та технологій захисту навколишнього середовища',
         'Екології та технологій захисту навколишнього середовища'),
        ('Економіки', 'Економіки'),
        ('Інженерії машин транспортного будівництва', 'Інженерії машин транспортного будівництва'),
        ('Іноземних мов', 'Іноземних мов'),
        ('Іноземної філології та перекладу', 'Іноземної філології та перекладу'),
        ('Інформаційних систем і технологій', 'Інформаційних систем і технологій'),
        ('Інформаційно-аналітичної діяльності та інформаційної безпеки',
         'Інформаційно-аналітичної діяльності та інформаційної безпеки'),
        ('Комп’ютерної, інженерної графіки та дизайну', 'Комп’ютерної, інженерної графіки та дизайну'),
        ('Конституційного та адміністративного права', 'Конституційного та адміністративного права'),
        ('Менеджменту', 'Менеджменту'),
        ('Міжнародних перевезень та митного контролю', 'Міжнародних перевезень та митного контролю'),
        ('Мостів, тунелів та гідротехнічних споруд', 'Мостів, тунелів та гідротехнічних споруд'),
        ('Опору матеріалів і машинознавства', 'Опору матеріалів і машинознавства'),
        ('Системного проєктування об’єктів транспортної інфраструктури та геодезії',
         'Системного проєктування об’єктів транспортної інфраструктури та геодезії'),
        ('Теоретичної та прикладної механіки', 'Теоретичної та прикладної механіки'),
        ('Теорії та історії держави і права', 'Теорії та історії держави і права'),
        ('Технічної експлуатації автомобілів та автосервісу', 'Технічної експлуатації автомобілів та автосервісу'),
        ('Tранспортних систем та безпеки дорожнього руху', 'Tранспортних систем та безпеки дорожнього руху'),
        ('Tранспортних технологій', 'Tранспортних технологій'),
        ('Транспортного будівництва та управління майном', 'Транспортного будівництва та управління майном'),
        ('Транспортного права та логістики', 'Транспортного права та логістики'),
        ('Туризму', 'Туризму'),
        ('Фізичного виховання і спорту', 'Фізичного виховання і спорту'),
        ('Філософії та педагогіки', 'Філософії та педагогіки'),
        ('Фінанси, облік і аудит', 'Фінанси, облік і аудит'),
    ]

    # Поля, які заповнює система або вручну користувач
    code = models.CharField(max_length=20, unique=True)  # Унікальний реєстраційний код
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    patronymic = models.CharField(max_length=50)
    faculty = models.CharField(max_length=200, choices=FACULTY_CHOICES)  # Назва кафедри / факультету
    group = models.CharField(max_length=50)  # Номер навчальної групи

    def __str__(self):
        return f"{self.code} — {self.last_name} {self.first_name}"  # Як відображається в адмінці



# 🔹 Модель коду викладача — використовується для підтвердження права на реєстрацію з роллю "lecturer"
class LecturerCode(models.Model):
    # Перелік посад для викладачів
    POSITION_CHOICES = [
        ('assistant', 'Асистент'),
        ('senior_lecturer', 'Старший викладач'),
        ('associate_professor', 'Доцент'),
        ('professor', 'Професор'),
        ('head_of_department', 'Завідувач кафедри'),
    ]

    code = models.CharField(max_length=20, unique=True)  # Унікальний код для реєстрації викладача
    first_name = models.CharField(max_length=50)         # Імʼя
    last_name = models.CharField(max_length=50)          # Прізвище
    patronymic = models.CharField(max_length=50)         # По-батькові
    job_position = models.CharField(max_length=50, choices=POSITION_CHOICES)  # Посада з обмеженого списку

    def __str__(self):
        # Відображення запису в адмінці — зручно для перегляду
        return f"{self.code} — {self.last_name} {self.first_name}"



# 🔹 Модель коду менеджера — використовується для підтвердження права на реєстрацію з роллю "manager"
class ManagerCode(models.Model):
    # Ті самі посади, що і для викладача — може бути переглянуто пізніше, якщо будуть відмінності
    POSITION_CHOICES = [
        ('assistant', 'Асистент'),
        ('senior_lecturer', 'Старший викладач'),
        ('associate_professor', 'Доцент'),
        ('professor', 'Професор'),
        ('head_of_department', 'Завідувач кафедри'),
    ]

    code = models.CharField(max_length=20, unique=True)  # Унікальний реєстраційний код
    first_name = models.CharField(max_length=50)         # Імʼя
    last_name = models.CharField(max_length=50)          # Прізвище
    patronymic = models.CharField(max_length=50)         # По батькові
    job_position = models.CharField(max_length=50, choices=POSITION_CHOICES)  # Посада

    def __str__(self):
        # Відображення у списку моделей (наприклад, у Django Admin)
        return f"{self.code} — {self.last_name} {self.first_name}"

class RequestImage(models.Model):
    request = models.ForeignKey('Request', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='requests/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image {self.id} for Request {self.request.id}"

class LocationUnit(models.Model):
    LOCATION_TYPE_CHOICES = [
        ("university", "Університет"),
        ("dormitory", "Гуртожиток"),
    ]

    name = models.CharField(max_length=100)  # Назва: Наприклад, "Корпус на Видубичах"
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPE_CHOICES)
    street_name = models.CharField(max_length=100)
    building_number = models.CharField(max_length=20)
    comment = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} — {self.street_name} {self.building_number}"

