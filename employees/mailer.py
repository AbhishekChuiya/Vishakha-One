"""Send portal e-mails reliably and keep a delivery log.

* Temporary problems (server busy, connection dropped, timeout) are retried: up to 3 attempts.
* Permanent problems (wrong SMTP login, address refused) are not retried; they are logged with the reason.
* At most `VONE_EMAIL_LIMIT_PER_HOUR` (default 5) e-mails of one kind are sent to one address per hour.
  The count comes from the database, so it is the same on every server worker.
* Nothing here raises: the caller shows the same neutral page whether or not the mail went out.
"""
import logging
import smtplib
import time
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import EmailDelivery

logger = logging.getLogger(__name__)

RETRY_DELAYS = (0, 1.5, 4.0)  # seconds to wait before attempt 1, 2 and 3
PERMANENT_ERRORS = (
    smtplib.SMTPAuthenticationError,
    smtplib.SMTPRecipientsRefused,
    smtplib.SMTPSenderRefused,
    smtplib.SMTPNotSupportedError,
)


def describe_mail_error(exc):
    """Short, password-free description of a mail failure."""
    code = getattr(exc, "smtp_code", None)
    detail = getattr(exc, "smtp_error", b"")
    if isinstance(detail, bytes):
        detail = detail.decode("utf-8", "replace")
    if code:
        return f"{type(exc).__name__} {code} {str(detail)[:140]}"
    return type(exc).__name__


def _record(purpose, recipient, status, attempts=0, error=""):
    try:
        EmailDelivery.objects.create(purpose=purpose, recipient=recipient[:254], status=status,
                                     attempts=attempts, error=error[:200])
    except Exception as exc:  # e.g. migration not applied yet: never block the e-mail itself
        logger.error("E-mail log could not be written (%s).", type(exc).__name__)


def _sent_recently(purpose, recipient, window):
    try:
        return EmailDelivery.objects.filter(
            purpose=purpose, recipient__iexact=recipient, status="sent",
            created_at__gte=timezone.now() - timedelta(seconds=window)).count()
    except Exception:
        return 0


def send_tracked(*, purpose, recipient, subject, text_body, html_body=None, limit=None, window=3600):
    """Send one e-mail. Returns True when the mail server accepted it."""
    limit = limit if limit is not None else int(getattr(settings, "VONE_EMAIL_LIMIT_PER_HOUR", 5))
    if _sent_recently(purpose, recipient, window) >= limit:
        _record(purpose, recipient, "throttled")
        logger.warning("E-mail skipped: hourly limit reached (%s).", purpose)
        return False
    error = ""
    attempts = 0
    for delay in RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        attempts += 1
        try:
            message = EmailMultiAlternatives(subject=subject, body=text_body, to=[recipient])
            if html_body:
                message.attach_alternative(html_body, "text/html")
            message.send()
        except Exception as exc:
            error = describe_mail_error(exc)
            if isinstance(exc, PERMANENT_ERRORS):
                break
            continue
        _record(purpose, recipient, "sent", attempts)
        return True
    _record(purpose, recipient, "failed", attempts, error)
    logger.error("E-mail could not be sent after %s attempt(s) (%s): %s", attempts, purpose, error)
    return False
