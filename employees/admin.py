from django.contrib import admin
from .models import EmailDelivery, EmployeeProfile


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "company_email", "user", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("employee_id", "company_email", "user__username", "user__first_name", "user__last_name")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("employee_id",)



@admin.register(EmailDelivery)
class EmailDeliveryAdmin(admin.ModelAdmin):
    """Read-only log of every e-mail the portal tried to send. Use it to see why a mail did not arrive."""
    list_display = ("created_at", "purpose", "recipient", "status", "attempts", "error")
    list_filter = ("status", "purpose")
    search_fields = ("recipient", "error")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
