from typing import List

from allauth.account.signals import user_signed_up
from django.core import mail
from django.dispatch import receiver
from django.template.loader import render_to_string


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


def build_registered_message(user, socialaccount):
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


def send_registered_notice_email(user, socialaccount):
    print('Sending registration message to ', user)
    messages = [build_registered_message(user, socialaccount)]
    with mail.get_connection() as connection:
        connection.send_messages(messages)


@receiver(user_signed_up)
def user_signed_up_listener(sender, user, **kwargs):
    for socialaccount in user.socialaccount_set.all():
        send_registered_notice_email(user, socialaccount)
