from django.conf import settings

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    """New accounts can only be created when OPEN_SITE is on"""

    def is_open_for_signup(self, request):
        return settings.OPEN_SITE


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Google sign in can only create new accounts when OPEN_SITE is on,
    existing users can always use it"""

    def is_open_for_signup(self, request, sociallogin):
        return settings.OPEN_SITE
