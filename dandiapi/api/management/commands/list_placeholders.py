from __future__ import annotations
from django.contrib.auth.models import User
import djclick as click


@click.command()
def list_placeholders():
    """
    Return a list of all user emails who still have a placeholder in Django.

    This may be useful to contact all users who have yet to log in.
    """
    placeholder_emails = User.objects.filter(email__startswith='placeholder_').values_list(
        'email', flat=True
    )
    emails = [email[12:] for email in placeholder_emails]
    click.echo(' '.join(emails))
