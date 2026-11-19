"""Employee self-registration.

Flow: employee enters Employee ID + @vishakha.com email -> a time-limited signed link is
e-mailed to that mailbox -> opening the link lets them choose a password, which creates
their login account. The e-mailed link proves they control that company mailbox.
No account is created until the link is used.
"""
import logging
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.template.loader import render_to_string

from . import mailer
from .models import EmployeeProfile, is_company_email

logger = logging.getLogger(__name__)

SALT = "vone.employee-registration.v2"
EMPLOYEE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,31}$")


class ActivationError(Exception):
    """Registration could not be completed (generic, safe to show to the user)."""


def registration_enabled():
    return bool(getattr(settings, "VONE_SELF_REGISTRATION_ENABLED", True))


def link_max_age():
    return int(getattr(settings, "VONE_ACTIVATION_LINK_SECONDS", 24 * 60 * 60))


def identity_taken(employee_id, company_email):
    """True if this Employee ID / email / username already belongs to any account."""
    User = get_user_model()
    return (
        EmployeeProfile.objects.filter(
            Q(employee_id__iexact=employee_id) | Q(company_email__iexact=company_email)
        ).exists()
        or User.objects.filter(
            Q(username__iexact=employee_id.lower()) | Q(email__iexact=company_email)
        ).exists()
    )


def registrable_identity(employee_id, company_email):
    """Return (EMPLOYEE_ID, email) if this identity may register, else None."""
    employee_id = (employee_id or "").strip()
    company_email = (company_email or "").strip().lower()
    if not EMPLOYEE_ID_RE.match(employee_id) or not is_company_email(company_email):
        return None
    employee_id = employee_id.upper()
    if identity_taken(employee_id, company_email):
        return None
    return employee_id, company_email


def profile_for_email(company_email):
    """The existing employee profile owned by this mailbox, if any (None otherwise)."""
    company_email = (company_email or "").strip().lower()
    if not is_company_email(company_email):
        return None
    return EmployeeProfile.objects.filter(
        company_email__iexact=company_email, is_active=True).first()


def make_token(employee_id, company_email):
    return signing.dumps({"eid": employee_id, "em": company_email}, salt=SALT)


def identity_from_token(token):
    """Return (employee_id, email) for a valid, unexpired token whose identity is still free."""
    try:
        data = signing.loads(token, salt=SALT, max_age=link_max_age())
        identity = (data["eid"], data["em"])
    except (signing.BadSignature, KeyError, TypeError):
        return None
    if not EMPLOYEE_ID_RE.match(identity[0]) or not is_company_email(identity[1]):
        return None
    return None if identity_taken(*identity) else identity


def send_activation_email(employee_id, company_email, link):
    context = {"employee_id": employee_id, "link": link, "hours": max(1, link_max_age() // 3600)}
    return mailer.send_tracked(
        purpose="registration", recipient=company_email,
        subject="Complete your Vishakha One registration",
        text_body=render_to_string("accounts/email/activation_email.txt", context),
        html_body=render_to_string("accounts/email/activation_email.html", context),
    )


def send_already_registered_email(profile, login_url, reset_url):
    """Tell the mailbox owner they already have an account (sent only to that company mailbox)."""
    context = {"employee_id": profile.employee_id, "login_url": login_url, "reset_url": reset_url}
    return mailer.send_tracked(
        purpose="already_registered", recipient=profile.company_email,
        subject="You already have a Vishakha One account",
        text_body=render_to_string("accounts/email/already_registered_email.txt", context),
        html_body=render_to_string("accounts/email/already_registered_email.html", context),
    )


def unsaved_user_for(employee_id, company_email):
    return get_user_model()(username=employee_id.lower(), email=company_email)


def activate(employee_id, company_email, password):
    """Create the login account + employee profile (race-safe; plain employee, no permissions)."""
    User = get_user_model()
    try:
        with transaction.atomic():
            if identity_taken(employee_id, company_email):
                raise ActivationError("This activation link is no longer valid.")
            user = unsaved_user_for(employee_id, company_email)
            try:
                User._meta.get_field("username").run_validators(user.username)
            except ValidationError:
                raise ActivationError("This account cannot be created automatically.")
            user.set_password(password)
            user.save()
            # No staff flag, groups or permissions: registration never grants Content Manager access.
            EmployeeProfile.objects.create(
                user=user, employee_id=employee_id, company_email=company_email)
            return user
    except (ValidationError, IntegrityError):
        raise ActivationError("This account cannot be created automatically.")
