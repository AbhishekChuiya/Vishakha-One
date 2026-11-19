from django.apps import AppConfig


class ContenthubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'contenthub'

    def ready(self):
        from django.db.models.signals import post_save
        from .models import Announcement
        from . import push_signals
        post_save.connect(push_signals.announcement_saved, sender=Announcement, dispatch_uid='vone_push_announcement')
