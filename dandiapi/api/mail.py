from __future__ import annotations

from collections.abc import Iterable
import logging

from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

BASE_RENDER_CONTEXT = {
    'dandi_api_url': settings.DANDI_API_URL,
    'dandi_web_app_url': settings.DANDI_WEB_APP_URL,
}

# TODO: turn this into a Django setting
ADMIN_EMAIL = 'info@dandiarchive.org'


def user_greeting_name(user: User, socialaccount: SocialAccount = None) -> str:
    """Return a suitable name to greet the user with in an email."""
    from dandiapi.api.views.users import social_account_to_dict, user_to_dict

    if socialaccount is None:
        return user_to_dict(user)['name']
    else:
        social_user = social_account_to_dict(socialaccount)

        # it's possible to have social users without a name if they've signed up, not filled out
        # the questionnaire, and their github account has no attached name.
        if social_user.get('name'):
            return f'{social_user["name"]} (Github ID: {social_user["username"]})'
        else:
            return social_user['username']


def build_message(subject: str, message: str, to: list[str], html_message: str | None = None):
    email_message = mail.EmailMultiAlternatives(subject=subject, body=message, to=to)
    if html_message is not None:
        email_message.attach_alternative(html_message, 'text/html')
    return email_message


def build_removed_message(dandiset, removed_owner):
    render_context = {
        **BASE_RENDER_CONTEXT,
        'dandiset_name': dandiset.draft_version.name,
        'dandiset_identifier': dandiset.identifier,
    }
    # Email sent when a user is removed as an owner from a dandiset
    return build_message(
        subject=f'Removed from Dandiset "{dandiset.draft_version.name}"',
        message=render_to_string('api/mail/removed_message.txt', render_context),
        to=[removed_owner.email],
    )


def build_added_message(dandiset, added_owner):
    render_context = {
        **BASE_RENDER_CONTEXT,
        'dandiset_name': dandiset.draft_version.name,
        'dandiset_identifier': dandiset.identifier,
    }
    # Email sent when a user is added as an owner of a dandiset
    return build_message(
        subject=f'Added to Dandiset "{dandiset.draft_version.name}"',
        message=render_to_string('api/mail/added_message.txt', render_context),
        to=[added_owner.email],
    )


def send_ownership_change_emails(dandiset, removed_owners, added_owners):
    messages = [build_removed_message(dandiset, removed_owner) for removed_owner in removed_owners]
    messages += [build_added_message(dandiset, added_owner) for added_owner in added_owners]
    with mail.get_connection() as connection:
        connection.send_messages(messages)


def build_registered_message(user: User, socialaccount: SocialAccount):
    # Email sent to the DANDI list when a new user logs in for the first time
    return build_message(
        subject=f'DANDI: New user registered: {user.email}',
        message=render_to_string(
            'api/mail/registered_message.txt',
            {'greeting_name': user_greeting_name(user, socialaccount)},
        ),
        to=[ADMIN_EMAIL, user.email],
    )


def send_registered_notice_email(user: User, socialaccount: SocialAccount):
    logger.info(f'Sending registration message to {user}')
    messages = [build_registered_message(user, socialaccount)]
    with mail.get_connection() as connection:
        connection.send_messages(messages)


def build_new_user_messsage(user: User, socialaccount: SocialAccount = None):
    render_context = {
        **BASE_RENDER_CONTEXT,
        'username': user.username,
    }
    # Email sent to the DANDI list when a new user logs in for the first time
    return build_message(
        subject=f'DANDI: Review new user: {user.username}',
        message=render_to_string('api/mail/new_user_message.txt', render_context),
        to=[ADMIN_EMAIL],
    )


def send_new_user_message_email(user: User, socialaccount: SocialAccount):
    logger.info(f'Sending new user message for {user} to admins')
    messages = [build_new_user_messsage(user, socialaccount)]
    with mail.get_connection() as connection:
        connection.send_messages(messages)


def build_approved_user_message(user: User, socialaccount: SocialAccount = None):
    return build_message(
        subject='Your DANDI Account',
        message=render_to_string(
            'api/mail/approved_user_message.txt',
            {
                **BASE_RENDER_CONTEXT,
                'greeting_name': user_greeting_name(user, socialaccount),
            },
        ),
        to=[ADMIN_EMAIL, user.email],
    )


def send_approved_user_message(user: User, socialaccount: SocialAccount):
    logger.info(f'Sending approved user message to {user}')
    messages = [build_approved_user_message(user, socialaccount)]
    with mail.get_connection() as connection:
        connection.send_messages(messages)


def build_rejected_user_message(user: User, socialaccount: SocialAccount = None):
    return build_message(
        subject='Your DANDI Account',
        message=render_to_string(
            'api/mail/rejected_user_message.txt',
            {
                'greeting_name': user_greeting_name(user, socialaccount),
                'rejection_reason': user.metadata.rejection_reason,
            },
        ),
        to=[ADMIN_EMAIL, user.email],
    )


def send_rejected_user_message(user: User, socialaccount: SocialAccount):
    logger.info(f'Sending rejected user message to {user}')
    messages = [build_rejected_user_message(user, socialaccount)]
    with mail.get_connection() as connection:
        connection.send_messages(messages)


def build_pending_users_message(users: Iterable[User]):
    render_context = {**BASE_RENDER_CONTEXT, 'users': users}
    return build_message(
        subject='DANDI: new user registrations to review',
        message=render_to_string('api/mail/pending_users_message.txt', render_context),
        to=[ADMIN_EMAIL],
    )


def send_pending_users_message(users: Iterable[User]):
    logger.info(f'Sending pending users message to admins at {ADMIN_EMAIL}')
    messages = [build_pending_users_message(users)]
    with mail.get_connection() as connection:
        connection.send_messages(messages)
