from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType
from contenthub.models import Announcement, Event, Resource, JobOpening, NewJoiner

ROLE_MODELS = {
    'Reception': (Announcement, Event),
    'HR': (Announcement, JobOpening, NewJoiner),
    'Administration': (Announcement, Resource, Event),
}
ACTIONS = ('view', 'add', 'change')

class Command(BaseCommand):
    help = 'Create/update Content Manager groups and optionally assign an existing user.'

    def add_arguments(self, parser):
        parser.add_argument('--username', help='Existing Django username to assign')
        parser.add_argument('--role', choices=ROLE_MODELS.keys(), help='Role for --username')

    def handle(self, *args, **options):
        username, role = options['username'], options['role']
        if bool(username) != bool(role):
            raise CommandError('Provide --username and --role together, or neither.')
        user = None
        if username:
            user = get_user_model().objects.filter(username=username).first()
            if user is None:
                raise CommandError(f'User {username!r} does not exist. Create it first in Django Admin.')
            if not user.is_active:
                raise CommandError(f'User {username!r} is inactive.')
        for group_name, models in ROLE_MODELS.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            permissions = []
            for model in models:
                content_type = ContentType.objects.get_for_model(model)
                for action in ACTIONS:
                    codename = f'{action}_{model._meta.model_name}'
                    try:
                        permissions.append(Permission.objects.get(content_type=content_type, codename=codename))
                    except Permission.DoesNotExist:
                        raise CommandError(f'Missing permission {codename}. Run python manage.py migrate first.')
            # Replace only permissions on the group, not other groups or user permissions.
            group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(f'{group_name}: {len(permissions)} permissions configured'))
        if user:
            group = Group.objects.get(name=role)
            user.groups.add(group)
            self.stdout.write(self.style.SUCCESS(f'Assigned {user.username} to {role}.'))
            self.stdout.write(f'Permissions: {sorted(p for p in user.get_all_permissions() if p.startswith("contenthub."))}')
