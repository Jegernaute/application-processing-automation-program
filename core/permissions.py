from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "manager"


class IsStudentOrLecturer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ["student", "lecturer"]

from rest_framework.permissions import BasePermission

class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Якщо об'єкт має поле user напряму
        if hasattr(obj, 'user'):
            return obj.user == request.user
        # Якщо об'єкт має пов’язану заявку
        if hasattr(obj, 'request') and hasattr(obj.request, 'user'):
            return obj.request.user == request.user
        return False


class IsOwnerOrManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user

        # 👨‍💼 Менеджер — доступ до всіх заявок
        if user.role == "manager":
            if request.method in SAFE_METHODS:
                return True

            # Дозволені поля, які може надсилати менеджер
            allowed_fields = [
                "status",
                "rejection_comment",
                "assigned_master_name",
                "assigned_master_company",
                "assigned_master_phone",
                "assigned_company_phone",
                "work_date"
            ]
            # Якщо є хоча б 1 поле, яке не дозволене — блок
            return all(field in allowed_fields for field in view.request.data.keys())

        # 👤 Студент або викладач — тільки свої заявки
        if hasattr(obj, 'user') and obj.user == user:
            return obj.status in ["empty", "rejected"]

        # Усі інші — ні
        return False


