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

def render_request_completed_message(request_obj, manager_email):
    return (
        f"Ваша заявка №{request_obj.code} була завершена менеджером.\n"
        f"Якщо у вас є зауваження — зверніться за адресою: {manager_email} протягом 30 днів."
    )

def render_request_rejected_message(request_obj):
    return (
        f"Заявку №{request_obj.code} відхилено.\n"
        f"Причина: {request_obj.rejection_comment or 'не вказана'}."
    )

def render_request_approved_message(request_obj):
    return f"Заявка №{request_obj.code} схвалена. Очікуйте подальших дій."

def render_master_assigned_message(request_obj):
    return (
        f"Майстра призначено для заявки №{request_obj.code}.\n"
        f"Дата візиту: {request_obj.work_date.strftime('%d.%m %H:%M')}\n"
        f"Ім’я майстра: {request_obj.master_name}\n"
        f"Телефон: {request_obj.master_phone}"
    )
def render_user_confirmed_message(request_obj):
    return (
        f"Користувач підтвердив, що заявка №{request_obj.code} виконана.\n"
        f"Ви можете перевести її в статус 'Виконано'."
    )

def render_request_restored_message(request_obj):
    return (
        f"Ваша заявка №{request_obj.code}, яка була завершена, відновлена менеджером.\n"
        f"Вона знову активна для подальшої обробки."
    )
