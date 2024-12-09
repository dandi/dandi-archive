from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

if TYPE_CHECKING:
    from allauth.socialaccount.models import SocialLogin
    from django.contrib.auth.models import User


class DandiAccountAdapter(DefaultAccountAdapter):
    _USERNAME_SUFFIX = '-dandi'

    def populate_username(self, request, user: User):
        # Call the super class in case of potential side effects
        super().populate_username(request, user)
        user.username = str(uuid4()) + self._USERNAME_SUFFIX


class DandiSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin: SocialLogin, form=None):
        user: User = super().save_user(request, sociallogin, form)
        user.username = user.email
        user.save()
        return user
