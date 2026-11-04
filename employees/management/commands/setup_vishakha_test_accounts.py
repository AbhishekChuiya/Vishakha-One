from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from contenthub.models import Announcement, Event, Resource
from employees.models import EmployeeProfile


TEST_ACCOUNTS = (
    {
        "username": "employee_test",
        "employee_id": "TESTEMP001",
        "email": "employee_test@vishakha.com",
        "group": None,
        "first_name": "Employee Test",
    },
    {
        "username": "content_manager_test",
        "employee_id": "TESTCM001",
        "email": "content_manager_test@vishakha.com",
        "group": "Administration",
        "first_name": "Content Manager Test",
    },
    {
        "username": "content_manager_approver",
        "employee_id": "TESTAPP001",
        "email": "content_manager_approver@vishakha.com",
        "group": "Administration Approvers",
        "first_name": "Content Manager Approver",
    },
)


ROLE_SPECS = {
    "Administration": {
        Announcement: ("view", "add", "change"),
        Resource: ("view", "add", "change"),
        Event: ("view", "add", "change"),
    },
    "Administration Approvers": {
        Announcement: ("view", "change", "approve"),
        Resource: ("view", "change", "approve"),
        Event: ("view", "change", "approve"),
    },
}


class Command(BaseCommand):
    help = "Create/update the three Vishakha One test accounts and assign their test roles."

    def _password_for(self, account, user):
        while True:
            password = getpass(f"Set password for {account['username']}: ")
            confirmation = getpass("Confirm password: ")
            if not password:
                self.stderr.write("Password cannot be blank.")
                continue
            if password != confirmation:
                self.stderr.write("Passwords do not match. Try again.")
                continue
            try:
                validate_password(password, user=user)
            except ValidationError as exc:
                for error in exc.messages:
                    self.stderr.write(error)
                continue
            return password

    def _configure_group(self, name, model_permissions):
        group, _ = Group.objects.get_or_create(name=name)
        permissions = []
        for model, actions in model_permissions.items():
            content_type = ContentType.objects.get_for_model(model)
            for action in actions:
                codename = f"{action}_{model._meta.model_name}"
                permission = Permission.objects.filter(
                    content_type=content_type, codename=codename
                ).first()
                if permission is None:
                    raise CommandError(
                        f"Permission {codename} is missing. Run migrations first."
                    )
                permissions.append(permission)
        # Add only the required permissions; preserve any existing group permissions.
        group.permissions.add(*permissions)
        return group

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        groups = {
            name: self._configure_group(name, specs)
            for name, specs in ROLE_SPECS.items()
        }

        self.stdout.write(self.style.WARNING(
            "This command creates or resets passwords for the three TEST accounts only."
        ))
        for account in TEST_ACCOUNTS:
            user, created = User.objects.get_or_create(
                username=account["username"],
                defaults={"email": account["email"]},
            )
            user.email = account["email"]
            user.first_name = account["first_name"]
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
            user.groups.clear()
            user.user_permissions.clear()
            user.set_password(self._password_for(account, user))
            user.save()

            try:
                EmployeeProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "employee_id": account["employee_id"],
                        "company_email": account["email"],
                        "is_active": True,
                    },
                )
            except ValidationError as exc:
                raise CommandError(
                    f"Could not create profile for {account['username']}: {exc}"
                ) from exc

            if account["group"]:
                user.groups.add(groups[account["group"]])

            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(
                f"{action}: {account['username']} | Employee ID: {account['employee_id']} | "
                f"Email: {account['email']} | Role: {account['group'] or 'Employee'}"
            ))

        self.stdout.write(self.style.SUCCESS(
            "All three test accounts are ready. Store the passwords securely; they are not written to this project."
        ))
