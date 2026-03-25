from __future__ import annotations

from allauth.account.signals import user_signed_up
from corsheaders.signals import check_request_enabled
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from dandiapi.api.models import UserMetadata


@receiver(check_request_enabled, dispatch_uid='cors_allow_anyone_read_only')
def cors_allow_anyone_read_only(*, sender, request, **kwargs):
    """Allow any read-only request from any origin."""
    return request.method in ('GET', 'HEAD', 'OPTIONS')


@receiver(post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid='create_auth_token')
def create_auth_token(*, sender, instance=None, created=False, **kwargs):
    """Create an auth token for every new user."""
    if created:
        Token.objects.create(user=instance)


@receiver(user_signed_up)
def user_signed_up_listener(*, sender, user, **kwargs):
    """Create UserMetadata whenever a user signs up."""
    if settings.DANDI_AUTO_APPROVE_USERS:
        status = UserMetadata.Status.APPROVED
    else:
        status = UserMetadata.Status.INCOMPLETE
    UserMetadata.objects.get_or_create(user=user, status=status)
