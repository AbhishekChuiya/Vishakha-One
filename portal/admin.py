from django.contrib import admin
from .models import CompanyApplication

@admin.register(CompanyApplication)
class CompanyApplicationAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "url", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("name", "category")
    list_filter = ("category", "is_active")
