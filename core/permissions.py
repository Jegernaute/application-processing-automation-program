from rest_framework.permissions import BasePermission

class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "manager"


class IsStudentOrLecturer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ["student", "lecturer"]

class IsOwnerOrManager(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.role == "manager" or obj.user == request.user
