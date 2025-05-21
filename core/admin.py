from django.contrib import admin
from .models import StudentCode, LecturerCode, ManagerCode, Request, User

admin.site.register(StudentCode)
admin.site.register(LecturerCode)
admin.site.register(ManagerCode)
admin.site.register(Request)
admin.site.register(User)

