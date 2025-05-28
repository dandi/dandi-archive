from __future__ import annotations

import os
from typing import TYPE_CHECKING

from composed_configuration._allauth_support.management.commands import createsuperuser
from django.db.models.signals import post_save

from dandiapi.api.models.user import UserMetadata

if TYPE_CHECKING:
    from composed_configuration._allauth_support.createsuperuser import EmailAsUsernameProxyUser


def create_usermetadata(instance: EmailAsUsernameProxyUser, created: bool, **kwargs):
    if created and not hasattr(instance, '_usermetadata_created'):
        UserMetadata.objects.get_or_create(
            user=instance, 
            defaults={'status': UserMetadata.Status.APPROVED}
        )
        instance._usermetadata_created = True


class Command(createsuperuser.Command):
    def handle(self, *args, **kwargs) -> str | None:
        # Temporarily connect a post_save signal handler so that we can catch the creation of
        # this superuser. Note, we do this in the handle() method to ensure this only happens
        # when this management command is actually run.
        post_save.connect(create_usermetadata, sender=createsuperuser.user_model)

        # Save the return value of the parent class function so we can return it later
        return_value = super().handle(*args, **kwargs)

        # Set first_name and last_name from environment variables if provided
        first_name = os.environ.get('DJANGO_SUPERUSER_FIRST_NAME')
        last_name = os.environ.get('DJANGO_SUPERUSER_LAST_NAME')
        
        if first_name or last_name:
            # Find the user that was just created
            email = kwargs.get('email') or os.environ.get('DJANGO_SUPERUSER_EMAIL')
            if email:
                try:
                    user = createsuperuser.user_model.objects.get(email=email)
                    if first_name:
                        user.first_name = first_name
                    if last_name:
                        user.last_name = last_name
                    user.save()
                except createsuperuser.user_model.DoesNotExist:
                    pass

        # Disconnect the signal handler. This isn't strictly necessary, but this avoids any
        # unexpected behavior if, for example, someone extends this command and doesn't
        # realize there's a signal handler attached dynamically.
        post_save.disconnect(create_usermetadata, sender=createsuperuser.user_model)

        return return_value
