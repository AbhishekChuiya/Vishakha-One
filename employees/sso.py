"""Map a verified company SSO identity (Microsoft Entra SAML) to an employee account.

SSO only ever creates or signs in a plain employee account. It never grants groups,
permissions, staff or superuser rights, so Content Manager access stays separate.
"""
import logging
from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from . import activation
from .models import EmployeeProfile, is_company_email

logger = logging.getLogger(__name__)


@dataclass
class Identity:
    email: str = ""
    employee_id: str = ""
    first_name: str = ""
    last_name: str = ""


class SsoDenied(Exception):
    """Sign-in refused. `user_message` is safe to show: the person is already authenticated by Microsoft."""

    def __init__(self, code, user_message):
        super().__init__(code)
        self.code = code
        self.user_message = user_message


def _values(attributes, names):
    for name in names:
        for value in attributes.get(name) or []:
            value = str(value).strip()
            if value:
                yield value


def _first(attributes, names):
    return next(_values(attributes, names), "")


def identity_from_attributes(attributes, name_id=""):
    attributes = attributes or {}
    candidates = list(_values(attributes, settings.VONE_SAML_EMAIL_ATTRS)) + [str(name_id or "").strip()]
    email = next((c.lower() for c in candidates if is_company_email(c)), "")
    return Identity(
        email=email,
        employee_id=_first(attributes, settings.VONE_SAML_EMPLOYEE_ID_ATTRS),
        first_name=_first(attributes, settings.VONE_SAML_FIRST_NAME_ATTRS)[:150],
        last_name=_first(attributes, settings.VONE_SAML_LAST_NAME_ATTRS)[:150],
    )


def provision(identity):
    employee_id = identity.employee_id.strip()
    if not employee_id:
        raise SsoDenied(
            "no_employee_id",
            "Your Microsoft account did not provide an Employee ID, so an account cannot be created "
            "automatically. Please use \"New employee? Register here\" instead.",
        )
    if not activation.EMPLOYEE_ID_RE.match(employee_id):
        raise SsoDenied("bad_employee_id", "The Employee ID from your Microsoft account is not in a valid format. Contact IT.")
    employee_id = employee_id.upper()
    User = get_user_model()
    try:
        with transaction.atomic():
            if activation.identity_taken(employee_id, identity.email):
                raise SsoDenied(
                    "identity_taken",
                    "Your Employee ID or email is already linked to a different portal account. Contact IT.",
                )
            user = User(username=employee_id.lower(), email=identity.email,
                        first_name=identity.first_name, last_name=identity.last_name)
            user.set_unusable_password()  # password sign-in can be added later via "Forgot password"
            user.save()
            # Plain employee only: no staff flag, groups or permissions.
            EmployeeProfile.objects.create(user=user, employee_id=employee_id, company_email=identity.email)
            return user
    except (ValidationError, IntegrityError):
        raise SsoDenied("provision_failed", "Your account could not be created automatically. Contact IT.")


def resolve_user(identity):
    """Return (user, created). Raises SsoDenied when this person must not be signed in."""
    if not is_company_email(identity.email):
        raise SsoDenied("no_company_email", "Your Microsoft account did not provide a @vishakha.com email address.")
    profile = EmployeeProfile.objects.select_related("user").filter(
        company_email__iexact=identity.email).first()
    if profile is not None:
        user = profile.user
        if not profile.is_active or not user.is_active:
            raise SsoDenied("inactive", "Your portal account is inactive. Contact IT.")
        if (user.email or "").strip().lower() != profile.company_email:
            raise SsoDenied("email_mismatch", "Your portal account needs attention. Contact IT.")
        if identity.employee_id and identity.employee_id.strip().upper() != profile.employee_id:
            logger.warning("SSO Employee ID differs from portal account (profile %s).", profile.pk)
            raise SsoDenied(
                "id_mismatch",
                "The Employee ID in the company directory does not match your portal account. Contact IT.",
            )
        return user, False
    if not getattr(settings, "VONE_SSO_AUTO_PROVISION", True):
        raise SsoDenied(
            "no_account",
            "You do not have a portal account yet. Please use \"New employee? Register here\" first.",
        )
    return provision(identity), True
