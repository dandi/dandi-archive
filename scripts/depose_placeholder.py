from django.contrib.auth.models import User

from dandiapi.api.user_migration import copy_ownership


def run(*args):
    if len(args) != 2:
        print(
            'Usage: python manage.py runscript create_placeholder_users --script-args '
            '{placeholder_email} {github_email}'
        )
        return
    placeholder_email = args[0]
    github_email = args[1]

    placeholder_user = User.objects.get(email=placeholder_email)
    github_user = User.objects.get(email=github_email)

    print(f'Replacing {placeholder_email} with {github_email}')
    copy_ownership(placeholder_user, github_user)

    print(f'Deleting {placeholder_email}')
    placeholder_user.delete()
