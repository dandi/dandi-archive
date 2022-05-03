from __future__ import annotations

import logging

from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.db.models.query import QuerySet
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

BASE_RENDER_CONTEXT = {
    'dandi_api_url': settings.DANDI_API_URL,
    'dandi_web_app_url': settings.DANDI_WEB_APP_URL,
}

# TODO: turn this into a Django setting
ADMIN_EMAIL = 'info@dandiarchive.org'


def build_message(subject: str, message: str, to: list[str], html_message: str | None = None):
    message = mail.EmailMultiAlternatives(subject=subject, body=message, to=to)
    if html_message is not None:
        message.attach_alternative(html_message, 'text/html')
    return message


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
    render_context = {
        'name': socialaccount.extra_data.get('name', user.username),
        'github_id': socialaccount.extra_data['login'],
    }
    # Email sent to the DANDI list when a new user logs in for the first time
    return build_message(
        subject=f'DANDI: New user registered: {user.email}',
        message=render_to_string('api/mail/registered_message.txt', render_context),
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
    # import here to avoid circular dependency
    from dandiapi.api.views.users import social_account_to_dict, user_to_dict

    if socialaccount is None:
        native_user = user_to_dict(user)
        render_context = {
            **BASE_RENDER_CONTEXT,
            'name': native_user['name'],
            'github_id': None,
        }
    else:
        social_user = social_account_to_dict(socialaccount)
        render_context = {
            **BASE_RENDER_CONTEXT,
            'name': social_user['name'],
            'github_id': social_user['username'],
        }
    return build_message(
        subject='Your DANDI Account',
        message=render_to_string('api/mail/approved_user_message.txt', render_context),
        to=[ADMIN_EMAIL, user.email],
    )


def send_approved_user_message(user: User, socialaccount: SocialAccount):
    logger.info(f'Sending approved user message to {user}')
    messages = [build_approved_user_message(user, socialaccount)]
    with mail.get_connection() as connection:
        connection.send_messages(messages)


def build_rejected_user_message(user: User, socialaccount: SocialAccount = None):
    # import here to avoid circular dependency
    from dandiapi.api.views.users import social_account_to_dict, user_to_dict

    if socialaccount is None:
        native_user = user_to_dict(user)
        render_context = {
            'name': native_user['name'],
            'github_id': None,
            'rejection_reason': user.metadata.rejection_reason,
        }
    else:
        social_user = social_account_to_dict(socialaccount)
        render_context = {
            'name': social_user['name'],
            'github_id': social_user['username'],
            'rejection_reason': user.metadata.rejection_reason,
        }
    return build_message(
        subject='Your DANDI Account',
        message=render_to_string('api/mail/rejected_user_message.txt', render_context),
        to=[ADMIN_EMAIL, user.email],
    )


def send_rejected_user_message(user: User, socialaccount: SocialAccount):
    logger.info(f'Sending rejected user message to {user}')
    messages = [build_rejected_user_message(user, socialaccount)]
    with mail.get_connection() as connection:
        connection.send_messages(messages)


def build_pending_users_message(users: QuerySet | list[User]):
    render_context = {**BASE_RENDER_CONTEXT, 'users': users}
    return build_message(
        subject='DANDI: new user registrations to review',
        message=render_to_string('api/mail/pending_users_message.txt', render_context),
        to=[ADMIN_EMAIL],
    )


def send_pending_users_message(users: QuerySet | list[User]):
    logger.info(f'Sending pending users message to admins at {ADMIN_EMAIL}')
    messages = [build_pending_users_message(users)]
    with mail.get_connection() as connection:
        connection.send_messages(messages)
