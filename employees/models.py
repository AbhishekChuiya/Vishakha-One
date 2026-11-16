from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models


COMPANY_EMAIL_DOMAIN = "vishakha.com"


def is_company_email(value):
    value = (value or "").strip().lower()
    return value.endswith(f"@{COMPANY_EMAIL_DOMAIN}") and value.count("@") == 1


class EmployeeProfile(models.Model):
    """Company identity details linked to Django's authentication account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )
    employee_id = models.CharField(max_length=32, unique=True, db_index=True)
    company_email = models.EmailField(max_length=254, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("employee_id",)
        verbose_name = "employee profile"
        verbose_name_plural = "employee profiles"

    def clean(self):
        super().clean()
        self.employee_id = (self.employee_id or "").strip().upper()
        self.company_email = (self.company_email or "").strip().lower()
        if not self.employee_id:
            raise ValidationError({"employee_id": "Employee ID is required."})
        if self.company_email:
            try:
                validate_email(self.company_email)
            except ValidationError:
                raise ValidationError({"company_email": "Enter a valid company email address."})
            if not is_company_email(self.company_email):
                raise ValidationError({
                    "company_email": "Only email addresses ending in @vishakha.com are allowed."
                })

    def save(self, *args, **kwargs):
        self.employee_id = (self.employee_id or "").strip().upper()
        self.company_email = (self.company_email or "").strip().lower()
        self.full_clean()
        super().save(*args, **kwargs)
        # Keep Django's standard email field in sync for admin and Content Manager use.
        if self.user_id and self.user.email != self.company_email:
            type(self.user).objects.filter(pk=self.user_id).update(email=self.company_email)

    def __str__(self):
        return f"{self.employee_id} — {self.company_email}"


class SsoLoginState(models.Model):
    """One in-flight company-SSO sign-in (short-lived, single-use).

    Kept in the database rather than the browser session because Microsoft posts the
    sign-in result back from another site, where browsers do not send our session cookie.
    """

    state = models.CharField(max_length=64, unique=True, db_index=True)
    request_id = models.CharField(max_length=100)
    nonce = models.CharField(max_length=64)
    next_url = models.CharField(max_length=500, blank=True)
    # Verified by Microsoft but no account yet and no Employee ID claim: kept here while the
    # person types their Employee ID (never trusted from the browser).
    email = models.EmailField(blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "SSO sign-in state"
        verbose_name_plural = "SSO sign-in states"
