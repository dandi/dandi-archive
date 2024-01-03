from __future__ import annotations
from django.contrib.auth.models import User
import djclick as click

from dandiapi.api.user_migration import depose_placeholder


@click.command()
def depose_placeholders():
    for user in User.objects.all():
        depose_placeholder(user)
