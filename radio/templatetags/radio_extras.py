from django import template
from django.conf import settings

from radio.models import SiteOption

register = template.Library()

# Allow settings in VISABLE_SETTINGS to be aviliable
@register.simple_tag()
def get_setting(value):
    visable_settings = getattr(settings, 'VISABLE_SETTINGS', [])
    if value in visable_settings:
        return getattr(settings, value, False)
    for opt in SiteOption.objects.filter(name=value, javascript_visible=True):
        return opt.value_boolean_or_string()
    return None
    
