from django import template
from contenthub.models import Announcement

register = template.Library()

@register.simple_tag
def published_company_notices():
    return Announcement.objects.visible().filter(category='announcement').order_by('-published_at')[:30]
