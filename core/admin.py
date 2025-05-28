from django.contrib import admin
from .models import StudentCode, LecturerCode, ManagerCode, Request, User, RequestImage, LocationUnit

admin.site.register(StudentCode)
admin.site.register(LecturerCode)
admin.site.register(ManagerCode)
admin.site.register(User)
admin.site.register(RequestImage)

class RequestAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "created_at", "updated_at")

admin.site.register(Request, RequestAdmin)

@admin.register(LocationUnit)
class LocationUnitAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "location_type", "street_name", "building_number", "is_active")
    list_filter = ("location_type", "is_active")
    search_fields = ("name", "street_name", "building_number")
