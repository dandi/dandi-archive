from django.contrib.auth.models import User
import djclick as click

from dandiapi.api.user_migration import copy_ownership


@click.command()
@click.argument('placeholder_email')
@click.argument('github_email')
def depose_placeholder(*, placeholder_email: str, github_email: str):
    placeholder_user = User.objects.get(email=placeholder_email)
    github_user = User.objects.get(email=github_email)

    click.echo(f'Replacing {placeholder_email} with {github_email}')
    copy_ownership(placeholder_user, github_user)

    click.echo(f'Deleting {placeholder_email}')
    placeholder_user.delete()
