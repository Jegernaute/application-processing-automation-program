from django.core.mail import send_mail
from django.conf import settings


def send_status_email(to_email, subject, message):
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
        fail_silently=False,  # Можна True у проді
    )

def create_notification(user, title: str, message: str):
    """
    Створює внутрішнє системне сповіщення (наприклад, про зміну статусу заявки).

    Поки що — заглушка.
    """
    # TODO: реалізувати модель Notification
    print(f"[NOTIFY] {user.email}: {title} — {message}")