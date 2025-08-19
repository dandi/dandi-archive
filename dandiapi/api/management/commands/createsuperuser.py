from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models.signals import post_save
from resonant_settings.allauth_support.management.commands import createsuperuser

from dandiapi.api.models.user import UserMetadata

if TYPE_CHECKING:
    from resonant_settings.allauth_support.createsuperuser import EmailAsUsernameProxyUser


def create_usermetadata(instance: EmailAsUsernameProxyUser, *args, **kwargs):
    UserMetadata.objects.create(user=instance, status=UserMetadata.Status.APPROVED)


class Command(createsuperuser.Command):
    def handle(self, *args, **kwargs) -> str | None:
        # Temporarily connect a post_save signal handler so that we can catch the creation of
        # this superuser. Note, we do this in the handle() method to ensure this only happens
        # when this management command is actually run.
        post_save.connect(create_usermetadata, sender=createsuperuser.user_model)

        # Save the return value of the parent class function so we can return it later
        return_value = super().handle(*args, **kwargs)

        # Disconnect the signal handler. This isn't strictly necessary, but this avoids any
        # unexpected behavior if, for example, someone extends this command and doesn't
        # realize there's a signal handler attached dynamically.
        post_save.disconnect(create_usermetadata, sender=createsuperuser.user_model)

        return return_value
