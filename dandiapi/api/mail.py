import logging
from typing import List

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.core import mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def build_message(subject: str, message: str, to: List[str], html_message: str):
    message = mail.EmailMultiAlternatives(subject=subject, body=message, to=to)
    message.attach_alternative(html_message, 'text/html')
    return message


def build_removed_message(dandiset, removed_owner):
    render_context = {
        'dandiset_name': dandiset.draft_version.name,
        'dandiset_identifier': dandiset.identifier,
    }
    # Email sent when a user is removed as an owner from a dandiset
    return build_message(
        subject=f'Removed from Dandiset "{dandiset.draft_version.name}"',
        message=render_to_string('api/mail/removed_message.txt', render_context),
        to=[removed_owner.email],
        html_message=render_to_string('api/mail/removed_message.html', render_context),
    )


def build_added_message(dandiset, added_owner):
    render_context = {
        'dandiset_name': dandiset.draft_version.name,
        'dandiset_identifier': dandiset.identifier,
    }
    # Email sent when a user is added as an owner of a dandiset
    return build_message(
        subject=f'Added to Dandiset "{dandiset.draft_version.name}"',
        message=render_to_string('api/mail/added_message.txt', render_context),
        to=[added_owner.email],
        html_message=render_to_string('api/mail/added_message.html', render_context),
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
        to=['dandi@mit.edu', user.email],
        html_message=render_to_string('api/mail/registered_message.html', render_context),
    )


def send_registered_notice_email(user: User, socialaccount: SocialAccount):
    logger.info(f'Sending registration message to {user}')
    messages = [build_registered_message(user, socialaccount)]
    with mail.get_connection() as connection:
        connection.send_messages(messages)


def build_new_user_messsage(user: User, socialaccount: SocialAccount = None):
    render_context = {
        'username': user.username,
    }
    # Email sent to the DANDI list when a new user logs in for the first time
    return build_message(
        subject=f'DANDI: New user registration to review: {user.username}',
        message=render_to_string('api/mail/new_user_message.txt', render_context),
        to=['dandi@mit.edu'],
        html_message=render_to_string('api/mail/new_user_message.html', render_context),
    )


def send_new_user_message_email(user: User, socialaccount: SocialAccount):
    logger.info(f'Sending new user message for {user} to admins')
    messages = [build_new_user_messsage(user, socialaccount)]
    with mail.get_connection() as connection:
        connection.send_messages(messages)


def build_approved_user_message(user: User, socialaccount: SocialAccount = None):
    # import here to avoid circular dependency
    from dandiapi.api.views.users import social_account_to_dict, user_to_dict

    logger.info(f'Sending approved user message to {user}')
    if socialaccount is None:
        native_user = user_to_dict(user)
        render_context = {
            'name': native_user['name'],
            'github_id': None,
        }
    else:
        social_user = social_account_to_dict(socialaccount)
        render_context = {
            'name': social_user['name'],
            'github_id': social_user['username'],
        }
    return build_message(
        subject='Your DANDI Account',
        message=render_to_string('api/mail/approved_user_message.txt', render_context),
        to=[user.email],
        html_message=render_to_string('api/mail/approved_user_message.html', render_context),
    )


def send_approved_user_message(user: User, socialaccount: SocialAccount):
    logger.info(f'Sending approved user message to {user}')
    messages = [build_approved_user_message(user, socialaccount)]
    with mail.get_connection() as connection:
        connection.send_messages(messages)


def build_rejected_user_message(user: User, socialaccount: SocialAccount = None):
    # import here to avoid circular dependency
    from dandiapi.api.views.users import social_account_to_dict, user_to_dict

    logger.info(f'Sending rejected user message to {user}')
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
        to=[user.email],
        html_message=render_to_string('api/mail/rejected_user_message.html', render_context),
    )


def send_rejected_user_message(user: User, socialaccount: SocialAccount):
    logger.info(f'Sending rejected user message to {user}')
    messages = [build_rejected_user_message(user, socialaccount)]
    with mail.get_connection() as connection:
        connection.send_messages(messages)
