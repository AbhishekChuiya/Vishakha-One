"""How a person's name is shown around the portal.

Real name if they saved one; otherwise a friendly name made from their company e-mail
(abhishek.chuiya@vishakha.com -> "Abhishek Chuiya"); the employee ID only as a last resort.
"""
import re


def display_name(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return ""
    full = (user.get_full_name() or "").strip()
    if full:
        return full
    profile = getattr(user, "employee_profile", None)
    email = (getattr(user, "email", "") or (profile.company_email if profile else "") or "")
    local = email.split("@")[0]
    parts = [p for p in re.split(r"[._\-+]+", local) if p.isalpha()]
    if parts:
        return " ".join(p.capitalize() for p in parts[:3])
    return user.get_username()


def first_name(user):
    full = display_name(user)
    return full.split()[0] if full else ""
