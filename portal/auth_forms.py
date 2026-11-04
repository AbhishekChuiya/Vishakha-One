from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from employees import activation
from employees.models import EmployeeProfile, is_company_email
from . import auth_throttle


class EmployeeLoginForm(forms.Form):
    identifier = forms.CharField(
        label="Employee ID or company email",
        max_length=254,
        widget=forms.TextInput(attrs={
            "class": "auth-input",
            "placeholder": "Enter your Employee ID or company email",
            "autocomplete": "username",
            "autofocus": True,
        }),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "auth-input",
            "placeholder": "Enter your password",
            "autocomplete": "current-password",
        }),
    )

    error_messages = {
        "invalid_login": "Employee ID/email or password is incorrect, or the account is inactive.",
        "domain": "Only active @vishakha.com employee accounts can sign in.",
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        identifier = (cleaned_data.get("identifier") or "").strip()
        password = cleaned_data.get("password")
        if not identifier or not password:
            return cleaned_data

        if "@" in identifier:
            email = identifier.lower()
            if not is_company_email(email):
                raise ValidationError(self.error_messages["domain"], code="domain")
            profile = EmployeeProfile.objects.select_related("user").filter(
                company_email__iexact=email
            ).first()
        else:
            profile = EmployeeProfile.objects.select_related("user").filter(
                employee_id__iexact=identifier
            ).first()

        if profile is None or not profile.is_active or not is_company_email(profile.company_email):
            raise ValidationError(self.error_messages["invalid_login"], code="invalid_login")

        user = authenticate(
            self.request,
            username=profile.user.get_username(),
            password=password,
        )
        if (
            user is None
            or not user.is_active
            or (user.email or "").strip().lower() != profile.company_email
        ):
            raise ValidationError(self.error_messages["invalid_login"], code="invalid_login")

        self.user_cache = user
        return cleaned_data

    def get_user(self):
        return self.user_cache


class CompanyDomainAuthenticationForm(AuthenticationForm):
    """Keep Content Manager's username login while enforcing the company domain."""

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not is_company_email(user.email):
            raise ValidationError(
                "Only @vishakha.com accounts can access Content Manager.",
                code="invalid_company_email",
            )
        manager_permissions = (
            "contenthub.view_announcement", "contenthub.add_announcement", "contenthub.change_announcement",
            "contenthub.view_resource", "contenthub.add_resource", "contenthub.change_resource",
            "contenthub.view_event", "contenthub.add_event", "contenthub.change_event",
            "contenthub.view_jobopening", "contenthub.add_jobopening", "contenthub.change_jobopening",
            "contenthub.view_newjoiner", "contenthub.add_newjoiner", "contenthub.change_newjoiner",
            "contenthub.manage_canteen_menu",
        )
        if not user.is_superuser and not any(user.has_perm(code) for code in manager_permissions):
            raise ValidationError(
                "This account has not been granted Content Manager access. Contact your administrator.",
                code="content_manager_access_required",
            )



class RegistrationRequestForm(forms.Form):
    """Step 1 of activation: Employee ID + company email (must match an HR record)."""

    employee_id = forms.CharField(
        label="Employee ID", max_length=32,
        widget=forms.TextInput(attrs={
            "class": "auth-input", "placeholder": "Your Employee ID",
            "autocomplete": "off", "autofocus": True,
        }),
    )
    company_email = forms.EmailField(
        label="Company email", max_length=254,
        widget=forms.EmailInput(attrs={
            "class": "auth-input", "placeholder": "yourname@vishakha.com",
            "autocomplete": "email",
        }),
    )

    def clean_employee_id(self):
        value = (self.cleaned_data["employee_id"] or "").strip()
        if not activation.EMPLOYEE_ID_RE.match(value):
            raise ValidationError(
                "Employee ID must be 3-32 characters: letters, numbers, dot, dash or underscore.")
        return value

    def clean_company_email(self):
        email = (self.cleaned_data["company_email"] or "").strip().lower()
        if not is_company_email(email):
            raise ValidationError("Enter your @vishakha.com company email address.")
        return email


class ActivationSetPasswordForm(forms.Form):
    """Step 2 of activation: choose a password (after the e-mailed link is opened)."""

    password1 = forms.CharField(
        label="New password", strip=False,
        widget=forms.PasswordInput(attrs={"class": "auth-input", "autocomplete": "new-password", "autofocus": True}),
    )
    password2 = forms.CharField(
        label="Confirm password", strip=False,
        widget=forms.PasswordInput(attrs={"class": "auth-input", "autocomplete": "new-password"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2:
            if p1 != p2:
                self.add_error("password2", "The two passwords do not match.")
            else:
                try:
                    password_validation.validate_password(p1, self.user)
                except ValidationError as exc:
                    self.add_error("password1", exc)
        return cleaned

    @property
    def password_help(self):
        return password_validation.password_validators_help_text_html()


class EmployeePasswordResetForm(PasswordResetForm):
    """Reset by Employee ID or company email. The reply never reveals whether an account exists."""

    email = None  # replaced by `identifier`
    identifier = forms.CharField(
        label="Employee ID or company email", max_length=254,
        widget=forms.TextInput(attrs={
            "class": "auth-input", "placeholder": "Employee ID or company email",
            "autocomplete": "username", "autofocus": True,
        }),
    )

    def _matching_users(self):
        identifier = (self.cleaned_data.get("identifier") or "").strip()
        if not identifier:
            return []
        if "@" in identifier:
            if not is_company_email(identifier):
                return []
            profile = EmployeeProfile.objects.select_related("user").filter(
                company_email__iexact=identifier, is_active=True).first()
        else:
            profile = EmployeeProfile.objects.select_related("user").filter(
                employee_id__iexact=identifier, is_active=True).first()
        if (
            profile is None
            or not profile.user.is_active
            or not is_company_email(profile.company_email)
            or (profile.user.email or "").strip().lower() != profile.company_email
        ):
            return []
        return [profile.user]

    def save(self, domain_override=None, subject_template_name=None,
             email_template_name=None, use_https=False,
             token_generator=default_token_generator, from_email=None,
             request=None, html_email_template_name=None, extra_email_context=None):
        for user in self._matching_users():
            # Limit e-mails per employee (silently) so nobody can flood one mailbox.
            if not auth_throttle.allow("password-reset", user.email):
                continue
            current_site = get_current_site(request)
            context = {
                "email": user.email,
                "domain": domain_override or current_site.domain,
                "site_name": current_site.name,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "user": user,
                "token": token_generator.make_token(user),
                "protocol": "https" if use_https else "http",
                **(extra_email_context or {}),
            }
            try:
                self.send_mail(subject_template_name, email_template_name, context,
                               from_email, user.email, html_email_template_name=html_email_template_name)
            except Exception as exc:  # do not reveal mail failures to the requester
                import logging
                logging.getLogger(__name__).error(
                    "Password reset e-mail could not be sent (%s).", activation.describe_mail_error(exc))
