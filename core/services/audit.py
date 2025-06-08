from core.models import RequestAuditLog

def log_change(request_obj, changed_by, field, old_value, new_value):
    """
    Створює запис про зміну поля заявки у таблиці логів.
    """
    if old_value != new_value:
        RequestAuditLog.objects.create(
            request=request_obj,
            changed_by=changed_by,
            field=field,
            old_value=str(old_value) if old_value is not None else "",
            new_value=str(new_value) if new_value is not None else ""
        )
