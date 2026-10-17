from django.contrib import admin
from .models import Announcement, Resource, JobOpening, NewJoiner, Event


class PublishingAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'published_at', 'display_order')
    list_editable = ('is_published',)
    list_filter = ('is_published', 'published_at')
    search_fields = ('title', 'summary')
    date_hierarchy = 'published_at'


@admin.register(Announcement)
class AnnouncementAdmin(PublishingAdmin):
    list_display = ('title', 'category', 'is_published', 'published_at', 'display_order')
    list_filter = ('category', 'is_published', 'published_at')


@admin.register(Resource)
class ResourceAdmin(PublishingAdmin):
    list_display = ('title', 'kind', 'department', 'is_published', 'published_at', 'display_order')
    list_filter = ('kind', 'department', 'is_published', 'published_at')


@admin.register(JobOpening)
class JobOpeningAdmin(PublishingAdmin):
    list_display = ('title', 'department', 'location', 'deadline', 'is_published')


@admin.register(NewJoiner)
class NewJoinerAdmin(PublishingAdmin):
    list_display = ('employee_name', 'designation', 'department', 'joining_date', 'is_published')
    search_fields = ('employee_name', 'designation', 'department')


@admin.register(Event)
class EventAdmin(PublishingAdmin):
    list_display = ('title', 'starts_at', 'location', 'is_published')
