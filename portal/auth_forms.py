from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from employees import activation, mailer
from employees.models import EmployeeProfile, is_company_email
from django.template import loader
from django.urls import reverse


class EmployeeLoginForm(forms.Form):
    identifier = forms.CharField(
        label="Employee ID or company email",
        max_length=254,
        widget=forms.TextInput(attrs={
            "class": "auth-input",
            "placeholder": "Employee ID or company email",
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


def classify_reset_request(identifier):
    """Decide what a "forgot password" request should lead to.

    Returns (kind, value):
      ("reset", user)         active employee account: send a reset link to its company e-mail
      ("attention", email)    account exists but is inactive or inconsistent: tell the mailbox owner
      ("no_account", email)   a company e-mail with no account yet: tell the owner how to register
      ("none", None)          nothing can be sent (unknown Employee ID, or not a company address)
    """
    identifier = (identifier or "").strip()
    if not identifier:
        return "none", None
    if "@" in identifier:
        email = identifier.lower()
        if not is_company_email(email):
            return "none", None
        profile = EmployeeProfile.objects.select_related("user").filter(company_email__iexact=email).first()
        if profile is None:
            return "no_account", email
    else:
        profile = EmployeeProfile.objects.select_related("user").filter(employee_id__iexact=identifier).first()
        if profile is None:
            return "none", None
    user = profile.user
    if (
        not profile.is_active
        or not user.is_active
        or not is_company_email(profile.company_email)
        or (user.email or "").strip().lower() != profile.company_email
    ):
        return "attention", profile.company_email
    return "reset", user


class EmployeePasswordResetForm(PasswordResetForm):
    """Reset by Employee ID or company email. The page never reveals whether an account exists,
    but the mailbox owner always gets an e-mail that explains what to do next."""

    email = None  # replaced by `identifier`
    identifier = forms.CharField(
        label="Employee ID or company email", max_length=254,
        widget=forms.TextInput(attrs={
            "class": "auth-input", "placeholder": "Employee ID or company email",
            "autocomplete": "username", "autofocus": True,
        }),
    )

    def save(self, domain_override=None, subject_template_name=None,
             email_template_name=None, use_https=False,
             token_generator=default_token_generator, from_email=None,
             request=None, html_email_template_name=None, extra_email_context=None):
        kind, value = classify_reset_request(self.cleaned_data.get("identifier"))
        if kind == "none":
            return
        login_url = request.build_absolute_uri(reverse("accounts:login")) if request else ""
        register_url = request.build_absolute_uri(reverse("accounts:register")) if request else ""
        if kind in ("no_account", "attention"):
            purpose = "password_reset_no_account" if kind == "no_account" else "password_reset_attention"
            context = {"login_url": login_url, "register_url": register_url}
            template = "no_account" if kind == "no_account" else "account_attention"
            subject = ("You do not have a Vishakha One account yet" if kind == "no_account"
                       else "Your Vishakha One password could not be reset")
            mailer.send_tracked(
                purpose=purpose, recipient=value, subject=subject,
                text_body=loader.render_to_string(f"accounts/email/{template}_email.txt", context),
                html_body=loader.render_to_string(f"accounts/email/{template}_email.html", context),
            )
            return
        user = value
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
        subject = "".join(loader.render_to_string(subject_template_name, context).splitlines())
        mailer.send_tracked(
            purpose="password_reset", recipient=user.email, subject=subject,
            text_body=loader.render_to_string(email_template_name, context),
            html_body=loader.render_to_string(html_email_template_name, context) if html_email_template_name else None,
        )


class SsoEmployeeIdForm(forms.Form):
    """Shown once after a first company-SSO sign-in when Microsoft sent no Employee ID."""

    employee_id = forms.CharField(
        label="Employee ID", max_length=32,
        widget=forms.TextInput(attrs={
            "class": "auth-input", "placeholder": "Your Employee ID",
            "autocomplete": "off", "autofocus": True,
        }),
    )

    def clean_employee_id(self):
        value = (self.cleaned_data["employee_id"] or "").strip()
        if not activation.EMPLOYEE_ID_RE.match(value):
            raise ValidationError(
                "Employee ID must be 3-32 characters: letters, numbers, dot, dash or underscore.")
        return value
