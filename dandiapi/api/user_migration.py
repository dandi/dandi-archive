import logging

from allauth.account.signals import user_logged_in
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def copy_ownership(placeholder_user, user):
    """Copy dandiset ownership from a placeholder user to the real user."""
    from guardian.shortcuts import assign_perm, get_objects_for_user, remove_perm

    from dandiapi.api.models import Dandiset

    owned_dandisets = get_objects_for_user(placeholder_user, 'owner', Dandiset)
    logger.info('%s owns %s', placeholder_user, owned_dandisets)
    for dandiset in owned_dandisets:
        logger.info('Moving ownership on %s', dandiset.identifier)
        assign_perm('owner', user, dandiset)
        remove_perm('owner', placeholder_user, dandiset)


def depose_placeholder(user):
    """Replace a placeholder user with a real user, if a placeholder exists."""
    from django.contrib.auth.models import User

    placeholder_email = 'placeholder_' + user.email
    try:
        placeholder_user = User.objects.get(email=placeholder_email)
    except User.DoesNotExist:
        # No placeholder user, nothing to do
        return

    logger.info('Replacing %s with %s', placeholder_user, user)
    copy_ownership(placeholder_user, user)
    # The placeholder user has no further purpose, delete it
    logger.info('Deleting %s', placeholder_user)
    placeholder_user.delete()


@receiver(user_logged_in)
def user_log_in_listener(*, sender, user, **kwargs):
    """Attempt replace a placeholder user every time a real user logs in."""
    depose_placeholder(user)
