from django.core import mail

FROM_EMAIL = 'admin@api.dandiarchive.org'


def build_message(subject, message, to, html_message):
    message = mail.EmailMultiAlternatives(subject, message, FROM_EMAIL, [to.email])
    message.attach_alternative(html_message, 'text/html')
    return message


def removed_subject(dandiset):
    return f'Removed from Dandiset "{dandiset.most_recent_published_version.name}"'


def removed_message(dandiset):
    return f'You have been removed as an owner of Dandiset "{dandiset.most_recent_published_version.name}".'


def removed_html_message(dandiset):
    return (
        'You have been removed as an owner of Dandiset '
        f'<a href="https://dandiarchive.org/dandiset/{dandiset.identifier}">'
        f'{dandiset.most_recent_published_version.name}'
        '</a>.'
    )


def build_removed_message(dandiset, removed_owner):
    return build_message(
        subject=removed_subject(dandiset),
        message=removed_message(dandiset),
        to=removed_owner,
        html_message=removed_html_message(dandiset),
    )


def added_subject(dandiset):
    return f'Added to Dandiset "{dandiset.most_recent_published_version.name}"'


def added_message(dandiset):
    return f'You have been made an owner of Dandiset "{dandiset.most_recent_published_version.name}".'


def added_html_message(dandiset):
    return (
        'You have been made an owner of Dandiset '
        f'<a href="https://dandiarchive.org/dandiset/{dandiset.identifier}">'
        f'{dandiset.most_recent_published_version.name}'
        '</a>.'
    )


def build_added_message(dandiset, added_owner):
    return build_message(
        subject=added_subject(dandiset),
        message=added_message(dandiset),
        to=added_owner,
        html_message=added_html_message(dandiset),
    )


def send_ownership_change_emails(dandiset, removed_owners, added_owners):
    messages = [build_removed_message(dandiset, removed_owner) for removed_owner in removed_owners]
    messages += [build_added_message(dandiset, added_owner) for added_owner in added_owners]
    with mail.get_connection() as connection:
        connection.send_messages(messages)
