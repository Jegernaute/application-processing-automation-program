from datetime import timedelta
from django.utils.timezone import now

def can_set_done(request_obj):
    """
    Перевіряє, чи можна перевести заявку в статус 'done'.
    Повертає кортеж: (True/False, пояснення)
    """
    if request_obj.user_confirmed:
        return True, "Користувач підтвердив виконання"

    if request_obj.work_date and now() > request_obj.work_date + timedelta(days=1):
        return True, "Пройшов один день після дати візиту"

    return False, "Заявку не можна завершити — не підтверджено користувачем і не пройшов час"
