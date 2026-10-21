"""Run using: python manage.py shell -c "exec(open('scripts/uat_preflight.py', encoding='utf-8').read())" """
from django.conf import settings
from django.urls import reverse, resolve
from django.db import connection
from django.apps import apps

print('=== Vishakha One preflight ===')
print('DEBUG:', settings.DEBUG)
print('Hosts:', settings.ALLOWED_HOSTS)
print('DB engine:', settings.DATABASES['default']['ENGINE'])
for name in ('portal:home','portal:canteen_menu','content_manager:canteen_menu','portal:notifications'):
    try:
        url=reverse(name)
        print('PASS',name,url,resolve(url).view_name)
    except Exception as exc:
        print('FAIL',name,str(exc))
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        print('PASS database connectivity')
except Exception as exc:
    print('FAIL database connectivity',str(exc))
