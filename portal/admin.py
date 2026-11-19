from django.contrib import admin
from django.utils.html import format_html

from .models import CompanyApplication, HelpfulLink


@admin.register(CompanyApplication)
class CompanyApplicationAdmin(admin.ModelAdmin):
    list_display = ("logo_preview", "name", "category", "url", "is_active", "display_order")
    list_display_links = ("name",)
    list_editable = ("is_active", "display_order")
    search_fields = ("name", "category")
    list_filter = ("category", "is_active")
    readonly_fields = ("logo_preview",)
    fields = ("name", "description", "url", "category", "logo", "logo_preview", "icon_path", "display_order", "is_active")

    @admin.display(description="Logo")
    def logo_preview(self, obj):
        if obj and obj.logo_url:
            return format_html('<img src="{}" alt="" style="width:40px;height:40px;object-fit:contain;border-radius:8px;background:#fff;border:1px solid #ddd">', obj.logo_url)
        return "-"


@admin.register(HelpfulLink)
class HelpfulLinkAdmin(admin.ModelAdmin):
    list_display = ("title", "url", "icon", "display_order", "is_active")
    list_editable = ("icon", "display_order", "is_active")
    search_fields = ("title", "url")
