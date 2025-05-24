from django.contrib import admin
from .models import StudentCode, LecturerCode, ManagerCode, Request, User

admin.site.register(StudentCode)
admin.site.register(LecturerCode)
admin.site.register(ManagerCode)
admin.site.register(User)

class RequestAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "created_at", "updated_at")

admin.site.register(Request, RequestAdmin)

