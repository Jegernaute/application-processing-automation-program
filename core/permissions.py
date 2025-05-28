from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "manager"


class IsStudentOrLecturer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ["student", "lecturer"]

class IsOwnerOrManager(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        # Якщо це фото — отримуємо заявку через obj.request
        if hasattr(obj, 'request'):
            request_obj = obj.request

            # Менеджер має лише право читання
            if user.role == "manager":
                return request.method in SAFE_METHODS

            # Студент/викладач — тільки якщо його заявка та статус дозволяє
            return (
                request_obj.user == user and
                request_obj.status in ["empty", "pending"]
            )

        # Якщо це об'єкт заявки
        if hasattr(obj, 'user'):
            return obj.user == user or user.role == "manager"

        return False
