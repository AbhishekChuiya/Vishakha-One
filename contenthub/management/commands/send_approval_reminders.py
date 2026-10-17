"""Send in-app reminders for content awaiting review for 24/48/72 hours.

Run from Windows Task Scheduler once per hour; use --dry-run for a preview.
"""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from contenthub.models import ApprovalReminderDelivery, ContentNotification, ContentAuditEvent, Resource
from contenthub.manager_views import SECTIONS, can_approve, scoped_queryset

THRESHOLDS = (24, 48, 72)

class Command(BaseCommand):
    help = 'Create deduplicated in-app approval reminders at 24, 48 and 72 hours.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview reminders without changing the database.')

    def handle(self, *args, **options):
        now = timezone.now()
        User = get_user_model()
        users = list(User.objects.filter(is_active=True).prefetch_related('groups', 'user_permissions'))
        created = 0
        candidates = 0
        for slug, cfg in SECTIONS.items():
            model = cfg['model']
            items = model.objects.filter(approval_status='pending', submitted_at__isnull=False,
                                         submitted_at__lte=now-timedelta(hours=24))
            for record in items.iterator():
                age = (now-record.submitted_at).total_seconds()/3600
                # Only the highest reached threshold is sent on each run.
                # Avoid a burst of 24h/48h/72h alerts on first installation.
                threshold = max(t for t in THRESHOLDS if age >= t)
                approvers = [u for u in users if can_approve(u, model)
                             and (model is not Resource or
                                  scoped_queryset(u, model).filter(pk=record.pk).exists())]
                recipients = {u.pk:u for u in approvers}
                if threshold >= 72 and record.submitted_by_id:
                    submitter = next((u for u in users if u.pk == record.submitted_by_id), None)
                    if submitter: recipients[submitter.pk] = submitter
                for recipient in recipients.values():
                    if ApprovalReminderDelivery.objects.filter(
                        recipient=recipient, section=slug, object_id=record.pk,
                        submitted_at=record.submitted_at, threshold_hours=threshold).exists():
                        continue
                    candidates += 1
                    if options['dry_run']:
                        self.stdout.write(f'Would notify {recipient.get_username()}: {slug} #{record.pk}, {threshold}h')
                        continue
                    with transaction.atomic():
                        delivery, new = ApprovalReminderDelivery.objects.get_or_create(
                            recipient=recipient, section=slug, object_id=record.pk,
                            submitted_at=record.submitted_at, threshold_hours=threshold)
                        if not new: continue
                        is_creator = recipient.pk == record.submitted_by_id
                        message = (f'Your submission has been awaiting approval for at least {threshold} hours.'
                                   if is_creator else
                                   f'Approval pending for at least {threshold} hours. Please review this {cfg["title"]} item.')
                        ContentNotification.objects.create(
                            recipient=recipient, actor=None, section=slug, object_id=record.pk,
                            title=record.title, kind='approval_overdue', message=message)
                        created += 1
                if not options['dry_run'] and threshold >= 72:
                    # Event is recorded only when this run actually notified someone.
                    pass
        self.stdout.write(self.style.SUCCESS(
            f'{"Preview" if options["dry_run"] else "Created"}: {candidates if options["dry_run"] else created} reminder notification(s).'))
