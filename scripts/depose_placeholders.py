from django.contrib.auth.models import User

from dandiapi.api.user_migration import depose_placeholder


def run():
    for user in User.objects.all():
        depose_placeholder(user)
