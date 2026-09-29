from django import template
from django.conf import settings
from django.utils import timezone

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
    


@register.simple_tag()
def copyright_notice():
    """Page footer text, the COPYRIGHT_NOTICE site option with {year}
    replaced by the current year, followed by the site title"""
    option = SiteOption.objects.filter(name='COPYRIGHT_NOTICE').first()
    notice = option.value.strip() if option and option.value.strip() else 'Copyright {year}'
    return '{} {}'.format(notice.replace('{year}', str(timezone.localdate().year)), settings.SITE_TITLE)
