from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from dandiapi.api.models.email import SentEmail
from dandiapi.api.services.permissions.dandiset import get_dandiset_owners

if TYPE_CHECKING:
    from collections.abc import Iterable

    from allauth.socialaccount.models import SocialAccount
    from django.contrib.auth.models import User

    from dandiapi.api.models.dandiset import Dandiset

logger = logging.getLogger(__name__)

BASE_RENDER_CONTEXT = {
    'dandi_api_url': settings.DANDI_API_URL,
    'dandi_web_app_url': settings.DANDI_WEB_APP_URL,
}


def user_greeting_name(user: User, socialaccount: SocialAccount = None) -> str:
    """Return a suitable name to greet the user with in an email."""
    from dandiapi.api.views.users import social_account_to_dict, user_to_dict

    if socialaccount is None:
        return user_to_dict(user)['name']

    social_user = social_account_to_dict(socialaccount)

    # it's possible to have social users without a name if they've signed up, not filled out
    # the questionnaire, and their github account has no attached name.
    if social_user.get('name'):
        return f'{social_user["name"]} (Github ID: {social_user["username"]})'
    return social_user['username']


def build_message(  # noqa: PLR0913
    to: list[str],
    subject: str,
    message: str,
    html_message: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reply_to: list[str] | None = None,
):
    email_message = mail.EmailMultiAlternatives(
        subject=subject, body=message, to=to, cc=cc, bcc=bcc, reply_to=reply_to
    )
    if html_message is not None:
        email_message.attach_alternative(html_message, 'text/html')
    return email_message


def _get_html_content(message) -> str:
    """Extract HTML content from an EmailMultiAlternatives message."""
    if message.alternatives:
        return message.alternatives[0][0]
    return ''


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


def send_ownership_change_emails(
    dandiset, removed_owners, added_owners
) -> list[SentEmail]:
    """Send emails when dandiset ownership changes.

    Returns a list of SentEmail records for tracking purposes.
    """
    messages = [build_removed_message(dandiset, removed_owner) for removed_owner in removed_owners]
    messages += [build_added_message(dandiset, added_owner) for added_owner in added_owners]

    with mail.get_connection() as connection:
        connection.send_messages(messages)

    # Record sent emails
    sent_emails = []

    for removed_owner in removed_owners:
        message = build_removed_message(dandiset, removed_owner)
        sent_emails.append(
            SentEmail.record_email(
                subject=message.subject,
                to=list(message.to),
                text_content=message.body,
                template_name='ownership_removed',
                render_context={
                    'dandiset_identifier': dandiset.identifier,
                    'dandiset_name': dandiset.draft_version.name,
                },
                dandiset=dandiset,
                recipient_users=[removed_owner],
            )
        )

    for added_owner in added_owners:
        message = build_added_message(dandiset, added_owner)
        sent_emails.append(
            SentEmail.record_email(
                subject=message.subject,
                to=list(message.to),
                text_content=message.body,
                template_name='ownership_added',
                render_context={
                    'dandiset_identifier': dandiset.identifier,
                    'dandiset_name': dandiset.draft_version.name,
                },
                dandiset=dandiset,
                recipient_users=[added_owner],
            )
        )

    return sent_emails


def build_registered_message(user: User, socialaccount: SocialAccount):
    # Email sent to the DANDI list when a new user logs in for the first time
    return build_message(
        subject=f'DANDI: New user registered: {user.email}',
        message=render_to_string(
            'api/mail/registered_message.txt',
            {'greeting_name': user_greeting_name(user, socialaccount)},
        ),
        to=[settings.DANDI_ADMIN_EMAIL, user.email],
    )


def send_registered_notice_email(user: User, socialaccount: SocialAccount) -> SentEmail:
    """Send registration notice email.

    Returns the SentEmail record for tracking purposes.
    """
    logger.info('Sending registration message to %s', user)
    message = build_registered_message(user, socialaccount)

    with mail.get_connection() as connection:
        connection.send_messages([message])

    return SentEmail.record_email(
        subject=message.subject,
        to=list(message.to),
        text_content=message.body,
        template_name='registered_notice',
        render_context={
            'user_email': user.email,
            'greeting_name': user_greeting_name(user, socialaccount),
        },
        recipient_users=[user],
    )


def build_new_user_messsage(user: User, socialaccount: SocialAccount = None):
    render_context = {
        **BASE_RENDER_CONTEXT,
        'username': user.username,
    }
    # Email sent to the DANDI list when a new user logs in for the first time
    return build_message(
        subject=f'DANDI: Review new user: {user.username}',
        message=render_to_string('api/mail/new_user_message.txt', render_context),
        to=[settings.DANDI_ADMIN_EMAIL],
    )


def send_new_user_message_email(user: User, socialaccount: SocialAccount) -> SentEmail:
    """Send new user review message to admins.

    Returns the SentEmail record for tracking purposes.
    """
    logger.info('Sending new user message for %s to admins', user)
    message = build_new_user_messsage(user, socialaccount)

    with mail.get_connection() as connection:
        connection.send_messages([message])

    return SentEmail.record_email(
        subject=message.subject,
        to=list(message.to),
        text_content=message.body,
        template_name='new_user_review',
        render_context={
            'username': user.username,
        },
        # Note: recipient is admin email, not the user being reviewed
    )


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
        to=[settings.DANDI_ADMIN_EMAIL, user.email],
    )


def send_approved_user_message(user: User, socialaccount: SocialAccount) -> SentEmail:
    """Send account approval message.

    Returns the SentEmail record for tracking purposes.
    """
    logger.info('Sending approved user message to %s', user)
    message = build_approved_user_message(user, socialaccount)

    with mail.get_connection() as connection:
        connection.send_messages([message])

    return SentEmail.record_email(
        subject=message.subject,
        to=list(message.to),
        text_content=message.body,
        template_name='user_approved',
        render_context={
            'user_email': user.email,
            'greeting_name': user_greeting_name(user, socialaccount),
        },
        recipient_users=[user],
    )


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
        to=[settings.DANDI_ADMIN_EMAIL, user.email],
    )


def send_rejected_user_message(user: User, socialaccount: SocialAccount) -> SentEmail:
    """Send account rejection message.

    Returns the SentEmail record for tracking purposes.
    """
    logger.info('Sending rejected user message to %s', user)
    message = build_rejected_user_message(user, socialaccount)

    with mail.get_connection() as connection:
        connection.send_messages([message])

    return SentEmail.record_email(
        subject=message.subject,
        to=list(message.to),
        text_content=message.body,
        template_name='user_rejected',
        render_context={
            'user_email': user.email,
            'greeting_name': user_greeting_name(user, socialaccount),
            'rejection_reason': user.metadata.rejection_reason,
        },
        recipient_users=[user],
    )


def build_pending_users_message(users: Iterable[User]):
    render_context = {**BASE_RENDER_CONTEXT, 'users': users}
    return build_message(
        subject='DANDI: new user registrations to review',
        message=render_to_string('api/mail/pending_users_message.txt', render_context),
        to=[settings.DANDI_ADMIN_EMAIL],
    )


def send_pending_users_message(users: Iterable[User]) -> SentEmail:
    """Send pending users review message to admins.

    Returns the SentEmail record for tracking purposes.
    """
    logger.info('Sending pending users message to admins at %s', settings.DANDI_ADMIN_EMAIL)
    users_list = list(users)
    message = build_pending_users_message(users_list)

    with mail.get_connection() as connection:
        connection.send_messages([message])

    return SentEmail.record_email(
        subject=message.subject,
        to=list(message.to),
        text_content=message.body,
        template_name='pending_users_review',
        render_context={
            'user_count': len(users_list),
            'usernames': [u.username for u in users_list],
        },
        # Note: recipient is admin email, users are the subject of the email
    )


def build_dandiset_unembargoed_message(dandiset: Dandiset):
    dandiset_context = {
        'identifier': dandiset.identifier,
        'ui_link': f'{settings.DANDI_WEB_APP_URL}/dandiset/{dandiset.identifier}',
    }

    render_context = {
        **BASE_RENDER_CONTEXT,
        'dandiset': dandiset_context,
    }
    html_message = render_to_string('api/mail/dandiset_unembargoed.html', render_context)
    return build_message(
        subject='Your Dandiset has been unembargoed!',
        message=strip_tags(html_message),
        html_message=html_message,
        to=[owner.email for owner in get_dandiset_owners(dandiset)],
    )


def send_dandiset_unembargoed_message(dandiset: Dandiset) -> SentEmail:
    """Send dandiset unembargoed notification.

    Returns the SentEmail record for tracking purposes.
    """
    logger.info('Sending dandisets unembargoed message to dandiset %s owners.', dandiset.identifier)
    owners = list(get_dandiset_owners(dandiset))
    message = build_dandiset_unembargoed_message(dandiset)

    with mail.get_connection() as connection:
        connection.send_messages([message])

    return SentEmail.record_email(
        subject=message.subject,
        to=list(message.to),
        text_content=message.body,
        html_content=_get_html_content(message),
        template_name='dandiset_unembargoed',
        render_context={
            'dandiset_identifier': dandiset.identifier,
        },
        dandiset=dandiset,
        recipient_users=owners,
    )


def build_dandiset_unembargo_failed_message(dandiset: Dandiset):
    dandiset_context = {
        'identifier': dandiset.identifier,
    }

    render_context = {**BASE_RENDER_CONTEXT, 'dandiset': dandiset_context}
    html_message = render_to_string('api/mail/dandiset_unembargo_failed.html', render_context)
    return build_message(
        subject=f'DANDI: Unembargo failed for dandiset {dandiset.identifier}',
        message=strip_tags(html_message),
        html_message=html_message,
        to=[owner.email for owner in get_dandiset_owners(dandiset)],
        bcc=[settings.DANDI_DEV_EMAIL],
        reply_to=[settings.DANDI_ADMIN_EMAIL],
    )


def send_dandiset_unembargo_failed_message(dandiset: Dandiset) -> SentEmail:
    """Send dandiset unembargo failure notification.

    Returns the SentEmail record for tracking purposes.
    """
    logger.info(
        'Sending dandiset unembargo failed message for dandiset %s to dandiset owners and devs',
        dandiset.identifier,
    )
    owners = list(get_dandiset_owners(dandiset))
    message = build_dandiset_unembargo_failed_message(dandiset)

    with mail.get_connection() as connection:
        connection.send_messages([message])

    return SentEmail.record_email(
        subject=message.subject,
        to=list(message.to),
        text_content=message.body,
        html_content=_get_html_content(message),
        bcc=list(message.bcc) if message.bcc else [],
        reply_to=list(message.reply_to) if message.reply_to else [],
        template_name='dandiset_unembargo_failed',
        render_context={
            'dandiset_identifier': dandiset.identifier,
        },
        dandiset=dandiset,
        recipient_users=owners,
    )


def build_publish_reminder_message(dandiset: Dandiset):
    """Build an email reminding dandiset owners to publish their dandiset."""
    dandiset_context = {
        'identifier': dandiset.identifier,
        'name': dandiset.draft_version.name,
        'ui_link': f'{settings.DANDI_WEB_APP_URL}/dandiset/{dandiset.identifier}',
    }

    render_context = {
        **BASE_RENDER_CONTEXT,
        'dandiset': dandiset_context,
    }
    html_message = render_to_string('api/mail/publish_reminder.html', render_context)
    return build_message(
        subject=f'Reminder: Publish your Dandiset "{dandiset.draft_version.name}"',
        message=strip_tags(html_message),
        html_message=html_message,
        to=[owner.email for owner in get_dandiset_owners(dandiset)],
        reply_to=[settings.DANDI_ADMIN_EMAIL],
    )


def send_publish_reminder_message(dandiset: Dandiset) -> SentEmail:
    """Send an email reminding dandiset owners to publish their dandiset.

    Returns the SentEmail record for tracking purposes.
    """
    logger.info('Sending publish reminder message to dandiset %s owners.', dandiset.identifier)
    owners = list(get_dandiset_owners(dandiset))
    message = build_publish_reminder_message(dandiset)

    with mail.get_connection() as connection:
        connection.send_messages([message])

    # Record the sent email
    return SentEmail.record_email(
        subject=message.subject,
        to=list(message.to),
        text_content=message.body,
        html_content=_get_html_content(message),
        reply_to=list(message.reply_to) if message.reply_to else [],
        template_name='publish_reminder',
        render_context={
            'dandiset_identifier': dandiset.identifier,
            'dandiset_name': dandiset.draft_version.name,
        },
        dandiset=dandiset,
        recipient_users=owners,
    )
