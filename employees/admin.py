from django.contrib import admin
from .models import EmployeeProfile


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "company_email", "user", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("employee_id", "company_email", "user__username", "user__first_name", "user__last_name")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("employee_id",)
