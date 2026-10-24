from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[2]
def change(rel,func):
 p=root/rel
 if not p.exists(): print('MISSING:',rel);return
 a=p.read_text(encoding='utf-8');b=func(a)
 if a==b:print('UNCHANGED:',rel);return
 bak=p.with_name(p.name+'.bak_a1_8')
 if not bak.exists():shutil.copy2(p,bak)
 p.write_text(b,encoding='utf-8');print('UPDATED:',rel)
def home(s):
 import re
 s=re.sub(r'<a\s+href="\{% url \'portal:section\' \'apps\' %\}">View full directory[^<]*</a>','',s,flags=re.I)
 old='<button type="button" class="vone-notice-dismiss vone-notice-modern-close" aria-label="Dismiss {{ notice.title }}" title="Dismiss announcement">×</button>'
 new="""<form class="vone-home-dismiss-form" method="post" action="{% url 'portal:notification_read' notice.pk %}" data-dismiss-notice>{% csrf_token %}<button type="submit" class="vone-notice-modern-close" aria-label="Dismiss {{ notice.title }}" title="Dismiss announcement">×</button></form>"""
 s=s.replace(old,new)
 s=s.replace('class="vone-notice-read-form"','class="vone-notice-read-form" data-dismiss-notice')
 return s
def base(s):
 link="""<link rel="stylesheet" href="{% static 'css/a1_8_mobile_refinements.css' %}?v=1.0">"""
 script="""<script src="{% static 'js/a1_8_notice_dismiss.js' %}?v=1.0" defer></script>"""
 if link not in s:s=s.replace('</head>',link+'</head>',1)
 if script not in s:s=s.replace('</body>',script+'</body>',1)
 return s
def media(s):
 s=s.replace('let limit=6;',"let limit=window.matchMedia('(max-width: 767px)').matches?4:6;\n    let step=window.matchMedia('(max-width: 767px)').matches?4:6;")
 s=s.replace('limit+=6;update();','limit+=step;update();')
 anchor='    update();\n  }\n  // Separate News'
 if anchor in s:
  s=s.replace(anchor,"""    window.addEventListener('resize',()=>{
      const next=window.matchMedia('(max-width: 767px)').matches?4:6;
      if(step!==next){step=next;limit=next;update();}
    });
    update();
  }
  // Separate News""",1)
 return s
change('templates/portal/home.html',home)
change('templates/base.html',base)
change('static/js/employee_media_experience.js',media)
print('Finished A1.8. Run python manage.py check.')
