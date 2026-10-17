"""Send in-app reminders for content awaiting review for 24/48/72 hours.

Run from Windows Task Scheduler once per hour; use --dry-run for a preview.
"""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from django.core.management.base import CommandError
from django.utils import timezone
from contenthub.models import ApprovalReminderDelivery, ContentNotification, ContentAuditEvent, Resource
from contenthub.manager_views import SECTIONS, can_approve, scoped_queryset

THRESHOLDS = (24, 48, 72)

class Command(BaseCommand):
    help = 'Create deduplicated in-app approval reminders at 24, 48 and 72 hours.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview reminders without changing the database.')
        parser.add_argument('--thresholds', default=None, help='Comma-separated reminder hours, e.g. 24,48,72.')
        parser.add_argument('--escalate-after', type=int, default=None, help='Escalate at or after this age in hours.')
        parser.add_argument('--escalate-to', default=None, help='Comma-separated usernames of escalation recipients (must be authorized approvers).')

    def handle(self, *args, **options):
        now = timezone.now()
        configured = options['thresholds'] or getattr(settings, 'CONTENT_APPROVAL_REMINDER_HOURS', '24,48,72')
        try:
            thresholds = tuple(sorted(set(int(v.strip()) for v in str(configured).split(',') if v.strip())))
        except ValueError as exc:
            raise CommandError('Reminder thresholds must be comma-separated integers.') from exc
        if not thresholds or any(v < 1 or v > 8760 for v in thresholds):
            raise CommandError('Reminder thresholds must be between 1 and 8760 hours.')
        escalate_after = options['escalate_after']
        if escalate_after is None:
            escalate_after = getattr(settings, 'CONTENT_APPROVAL_ESCALATE_AFTER_HOURS', 72)
        if not isinstance(escalate_after, int) or escalate_after < 1 or escalate_after > 8760:
            raise CommandError('Escalation hours must be between 1 and 8760.')
        escalation_names = options['escalate_to']
        if escalation_names is None:
            escalation_names = getattr(settings, 'CONTENT_APPROVAL_ESCALATE_TO', '')
        escalation_names = {v.strip() for v in str(escalation_names).split(',') if v.strip()}
        # An escalation is tracked using its own threshold key, distinct from regular reminders.
        escalation_key = 50000 + escalate_after

        User = get_user_model()
        users = list(User.objects.filter(is_active=True).prefetch_related('groups', 'user_permissions'))
        created = 0
        candidates = 0
        for slug, cfg in SECTIONS.items():
            model = cfg['model']
            items = model.objects.filter(approval_status='pending', submitted_at__isnull=False,
                                         submitted_at__lte=now-timedelta(hours=min(thresholds[0], escalate_after)))
            for record in items.iterator():
                age = (now-record.submitted_at).total_seconds()/3600
                # Only the highest reached threshold is sent on each run.
                # Avoid a burst of 24h/48h/72h alerts on first installation.
                reached = [t for t in thresholds if age >= t]
                threshold = max(reached) if reached else None
                approvers = [u for u in users if can_approve(u, model)
                             and (model is not Resource or
                                  scoped_queryset(u, model).filter(pk=record.pk).exists())]
                recipients = {u.pk:u for u in approvers}
                if age >= escalate_after and record.submitted_by_id:
                    submitter = next((u for u in users if u.pk == record.submitted_by_id), None)
                    if submitter: recipients[submitter.pk] = submitter
                # Only approvers may be added as named escalation recipients.
                escalation_recipients = {u.pk:u for u in users if u.get_username() in escalation_names
                                         and can_approve(u, model)
                                         and (model is not Resource or scoped_queryset(u, model).filter(pk=record.pk).exists())}
                jobs = []
                if threshold is not None:
                    jobs.extend((u, threshold, False) for u in recipients.values())
                if age >= escalate_after:
                    jobs.extend((u, escalation_key, True) for u in escalation_recipients.values())
                for recipient, delivery_threshold, is_escalation in jobs:
                    if ApprovalReminderDelivery.objects.filter(
                        recipient=recipient, section=slug, object_id=record.pk,
                        submitted_at=record.submitted_at, threshold_hours=delivery_threshold).exists():
                        continue
                    candidates += 1
                    if options['dry_run']:
                        self.stdout.write(f'Would notify {recipient.get_username()}: {slug} #{record.pk}, {delivery_threshold} ({"escalation" if is_escalation else "reminder"})')
                        continue
                    with transaction.atomic():
                        delivery, new = ApprovalReminderDelivery.objects.get_or_create(
                            recipient=recipient, section=slug, object_id=record.pk,
                            submitted_at=record.submitted_at, threshold_hours=delivery_threshold)
                        if not new: continue
                        is_creator = recipient.pk == record.submitted_by_id
                        message = (f'Your submission has been awaiting approval for at least {threshold} hours.'
                                   if is_creator else
                                   f'Approval pending for at least {threshold} hours. Please review this {cfg["title"]} item.')
                        if is_escalation:
                            message = f'Escalation: approval pending for at least {escalate_after} hours. Please review this {cfg["title"]} item.'
                        ContentNotification.objects.create(
                            recipient=recipient, actor=None, section=slug, object_id=record.pk,
                            title=record.title, kind='approval_escalation' if is_escalation else 'approval_overdue', message=message)
                        created += 1
        self.stdout.write(self.style.SUCCESS(
            f'{"Preview" if options["dry_run"] else "Created"}: {candidates if options["dry_run"] else created} reminder notification(s).'))
