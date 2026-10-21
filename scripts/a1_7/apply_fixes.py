from pathlib import Path
import shutil,re
root=Path(__file__).resolve().parents[2]
def patch(name,func):
 p=root/name
 if not p.exists(): print('MISSING',name);return
 a=p.read_text(encoding='utf8');b=func(a)
 if a==b:print('UNCHANGED',name);return
 bak=p.with_name(p.name+'.bak_a1_7')
 if not bak.exists():shutil.copy2(p,bak)
 p.write_text(b,encoding='utf8');print('UPDATED',name)
def home(s):
 old='<button type="button" class="vone-notice-dismiss vone-notice-modern-close" aria-label="Dismiss {{ notice.title }}" title="Dismiss announcement">×</button>'
 new='''<form method="post" action="{% url 'portal:notification_read' notice.pk %}" class="vone-notice-read-form">{% csrf_token %}<input type="hidden" name="next" value="home"><button type="submit" class="vone-notice-modern-close" aria-label="Dismiss {{ notice.title }}" title="Dismiss announcement">×</button></form>'''
 s=s.replace(old,new)
 s=re.sub(r'<div class="vone-menu-snacks[^>]*>.*?</div>', '''<div class="vone-menu-snacks {% if day.menu.snacks %}is-special{% else %}is-regular{% endif %}">{% if day.menu.snacks %}<span class="vone-snack-icon" aria-hidden="true">✦</span><span class="vone-snack-copy"><small>CHEF'S SPECIAL</small><strong>{{ day.menu.snacks }}</strong></span>{% else %}<span class="vone-snack-icon" aria-hidden="true">☕</span><strong>Regular Snacks</strong>{% endif %}</div>''',s)
 s=re.sub(r'<script src="\{% static \'js/employee_notices.js\' %\}[^\"]*" defer></script>','',s)
 return s
def canteen(s):
 s=re.sub(r'<div class="vone-canteen-snacks[^>]*>.*?</div>', '''<div class="vone-canteen-snacks {% if day.menu.snacks %}is-special{% else %}is-regular{% endif %}">{% if day.menu.snacks %}<span aria-hidden="true">✦</span><strong>Chef's Special</strong><p>{{ day.menu.snacks }}</p>{% else %}<span aria-hidden="true">☕</span><strong>Regular Snacks</strong>{% endif %}</div>''',s)
 s=s.replace("{{ day.menu.snacks|default:'Not scheduled' }}","{% if day.menu.snacks %}{{ day.menu.snacks }}{% else %}Regular Snacks{% endif %}").replace("{{ day.menu.snacks|default:'Regular Snacks available' }}","{% if day.menu.snacks %}{{ day.menu.snacks }}{% else %}Regular Snacks{% endif %}")
 return s
def notifications(s):
 return re.sub(r'<script src="\{% static \'js/employee_notices.js\' %\}[^\"]*" defer></script>','',s)
def views(s):
 marker='def mark_announcement_read(request, pk):';i=s.find(marker)
 if i<0:raise RuntimeError('Cannot locate mark_announcement_read')
 j=s.find('\n@',i+len(marker));j=len(s) if j<0 else j
 part=s[i:j]
 if "request.POST.get('next')" not in part:
  old="    return redirect('portal:notifications')"
  if old not in part:raise RuntimeError('Unexpected read handler')
  part=part.replace(old,"    return redirect('portal:home' if request.POST.get('next') == 'home' else 'portal:notifications')",1)
  s=s[:i]+part+s[j:]
 return s
def base(s):
 link='''<link rel="stylesheet" href="{% static 'css/a1_7_notifications_snacks.css' %}?v=1.0">'''
 return s if link in s else s.replace('</head>',link+'</head>',1)
for name,func in [('templates/portal/home.html',home),('templates/portal/canteen_week.html',canteen),('templates/portal/notifications.html',notifications),('portal/views.py',views),('templates/base.html',base)]:patch(name,func)
print('Complete')
