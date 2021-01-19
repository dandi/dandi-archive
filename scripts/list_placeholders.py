"""
Return a list of all user emails who still have a placeholder in Django.

Run me:
python manage.py runscript list_placeholders

This may be useful to contact all users who have yet to log in.
"""

from django.contrib.auth.models import User


def run():
    placeholder_emails = User.objects.filter(email__startswith='placeholder_').values_list(
        'email', flat=True
    )
    emails = [email[12:] for email in placeholder_emails]
    print(' '.join(emails))
