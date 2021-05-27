from typing import List

from allauth.account.signals import user_signed_up
from django.core import mail
from django.dispatch import receiver


def build_message(subject: str, message: str, to: List[str], html_message: str):
    message = mail.EmailMultiAlternatives(subject=subject, body=message, to=to)
    message.attach_alternative(html_message, 'text/html')
    return message


# Email sent when a user is removed as an owner from a dandiset


def removed_subject(dandiset):
    return f'Removed from Dandiset "{dandiset.draft_version.name}"'


def removed_message(dandiset):
    return f'You have been removed as an owner of Dandiset "{dandiset.draft_version.name}".'


def removed_html_message(dandiset):
    return (
        'You have been removed as an owner of Dandiset '
        f'<a href="https://dandiarchive.org/dandiset/{dandiset.identifier}">'
        f'{dandiset.draft_version.name}'
        '</a>.'
    )


def build_removed_message(dandiset, removed_owner):
    return build_message(
        subject=removed_subject(dandiset),
        message=removed_message(dandiset),
        to=[removed_owner.email],
        html_message=removed_html_message(dandiset),
    )


# Email sent when a user is added as an owner of a dandiset


def added_subject(dandiset):
    return f'Added to Dandiset "{dandiset.draft_version.name}"'


def added_message(dandiset):
    return f'You have been made an owner of Dandiset "{dandiset.draft_version.name}".'


def added_html_message(dandiset):
    return (
        'You have been made an owner of Dandiset '
        f'<a href="https://dandiarchive.org/dandiset/{dandiset.identifier}">'
        f'{dandiset.draft_version.name}'
        '</a>.'
    )


def build_added_message(dandiset, added_owner):
    return build_message(
        subject=added_subject(dandiset),
        message=added_message(dandiset),
        to=[added_owner.email],
        html_message=added_html_message(dandiset),
    )


def send_ownership_change_emails(dandiset, removed_owners, added_owners):
    messages = [build_removed_message(dandiset, removed_owner) for removed_owner in removed_owners]
    messages += [build_added_message(dandiset, added_owner) for added_owner in added_owners]
    with mail.get_connection() as connection:
        connection.send_messages(messages)


# Email sent to the DANDI list when a new user logs in for the first time


def registered_subject(user):
    return f'DANDI: New user registered: {user.email}'


def registered_html_message(user, socialaccount):
    name = socialaccount.extra_data['name'] if 'name' in socialaccount.extra_data else user.username
    return f"""<p>Dear {name} (Github ID: {socialaccount.extra_data['login']}),</p>
<p>Welcome to DANDI. </p>
<p>You are now registered on the DANDI archive. Registering allows you to create Dandisets and upload data right away. You can also use the Jupyterhub (<a href="https://hub.dandiarchive.org">https://hub.dandiarchive.org</a>) for computing on dandisets in the cloud. </p>
<p>It may take up to 24 hours for your hub account to be activated and for your email to be registered with our Slack workspace.</p>
<p>Please post any <a href="https://github.com/dandi/helpdesk/discussions">questions</a> or <a href="https://github.com/dandi/helpdesk/issues">issues</a> at our <a href="https://github.com/dandi/helpdesk">Github helpdesk</a>.</p>
<p>Thank you for choosing DANDI for your neurophysiology data needs.</p>
<p>Sincerely,</p>
<p>The DANDI team</p>"""  # noqa: E501


def registered_message(user, socialaccount):
    name = socialaccount.extra_data['name'] if 'name' in socialaccount.extra_data else user.username
    return f"""Dear {name} (Github ID: {socialaccount.extra_data["login"]}),

Welcome to DANDI.

You are now registered on the DANDI archive. Registering allows you to create Dandisets and upload
data right away. You can also use the Jupyterhub (https://hub.dandiarchive.org) for computing on
dandisets in the cloud.

It may take up to 24 hours for your hub account to be activated and for your email to be registered
with our Slack workspace.

Please use the following links to post any questions or issues.

Discussions: https://github.com/dandi/helpdesk/discussions
Issues: https://github.com/dandi/helpdesk/issues

Thank you for choosing DANDI for your neurophysiology data needs.

Sincerely,

The DANDI team"""  # noqa: E501


def build_registered_message(user, socialaccount):
    return build_message(
        subject=registered_subject(user),
        message=registered_message(user, socialaccount),
        to=['dandi@mit.edu', user.email],
        html_message=registered_html_message(user, socialaccount),
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
