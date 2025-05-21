from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.conf import settings


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обовʼязковий')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser повинен мати is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser повинен мати is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    # Прибрати username — не обов'язково, але можна замінити логіку
    username = None

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50, blank=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    patronymic = models.CharField(max_length=50, blank=True)

    ROLE_CHOICES = [
        ('student', 'Студент'),
        ('lecturer', 'Викладач'),
        ('manager', 'Менеджер'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'  # ключ для логіну
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role']  # потрібні при createsuperuser

    def __str__(self):
        return f'{self.email} ({self.role})'


class Request(models.Model):
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

    STATUS_CHOICES = [
        ('pending', 'В обробці'),
        ('approved', 'Підтверджено'),
        ('rejected', 'Відхилено'),
        ('done', 'Виконано'),
        ('on_check', 'На перевірці'),
    ]

    name = models.CharField(max_length=255)
    type_request = models.CharField(max_length=50, choices=TYPE_CHOICES)
    description = models.TextField()
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requests')

    def __str__(self):
        return f"{self.name} ({self.get_type_request_display()}) - {self.status}"


class StudentCode(models.Model):
    FACULTY_CHOICES = [
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

    code = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    patronymic = models.CharField(max_length=50)
    faculty = models.CharField(max_length=200, choices=FACULTY_CHOICES)
    group = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.code} — {self.last_name} {self.first_name}"


class LecturerCode(models.Model):
    POSITION_CHOICES = [
        ('assistant', 'Асистент'),
        ('senior_lecturer', 'Старший викладач'),
        ('associate_professor', 'Доцент'),
        ('professor', 'Професор'),
        ('head_of_department', 'Завідувач кафедри'),
    ]

    code = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    patronymic = models.CharField(max_length=50)
    job_position = models.CharField(max_length=50, choices=POSITION_CHOICES)

    def __str__(self):
        return f"{self.code} — {self.last_name} {self.first_name}"


class ManagerCode(models.Model):
    POSITION_CHOICES = [
        ('assistant', 'Асистент'),
        ('senior_lecturer', 'Старший викладач'),
        ('associate_professor', 'Доцент'),
        ('professor', 'Професор'),
        ('head_of_department', 'Завідувач кафедри'),
    ]

    code = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    patronymic = models.CharField(max_length=50)
    job_position = models.CharField(max_length=50, choices=POSITION_CHOICES)

    def __str__(self):
        return f"{self.code} — {self.last_name} {self.first_name}"
