from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from contenthub.models import Announcement, Resource, JobOpening, NewJoiner, Event

class Command(BaseCommand):
    help = 'Create additional Step 11 content creator/approver roles without changing existing groups.'

    def handle(self, *args, **kwargs):
        roles = {
            'Policy Editors': [(Resource, ('view', 'add', 'change'))],
            'Reception Approvers': [(Announcement, ('view', 'change', 'approve')), (Event, ('view', 'change', 'approve'))],
            'HR Approvers': [(Announcement, ('view', 'change', 'approve')), (JobOpening, ('view', 'change', 'approve')), (NewJoiner, ('view', 'change', 'approve'))],
            'Administration Approvers': [(Announcement, ('view', 'change', 'approve')), (Resource, ('view', 'change', 'approve')), (Event, ('view', 'change', 'approve'))],
        }
        for name, specs in roles.items():
            group, _ = Group.objects.get_or_create(name=name)
            perms = []
            for model, actions in specs:
                ct = ContentType.objects.get_for_model(model)
                for action in actions:
                    codename = f'{action}_{model._meta.model_name}'
                    try:
                        perms.append(Permission.objects.get(content_type=ct, codename=codename))
                    except Permission.DoesNotExist:
                        raise CommandError(f'Missing {codename}; run migrate first.')
            # Add only, so repeated runs don't revoke custom group permissions.
            group.permissions.add(*perms)
            self.stdout.write(self.style.SUCCESS(f'{name}: ready'))
        self.stdout.write('Assign employees to these groups via Django Admin > Users. Do not grant superuser.')
