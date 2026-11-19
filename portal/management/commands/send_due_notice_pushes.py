from django.core.management.base import BaseCommand

from portal import push


class Command(BaseCommand):
    help = "Send push notifications for scheduled company notices whose publish time has arrived. Run every few minutes from cron."

    def handle(self, *args, **options):
        if not push.enabled():
            self.stdout.write("Push is not configured (no VAPID keys); nothing to do.")
            return
        self.stdout.write(f"Notices pushed: {push.send_due_notices()}")
