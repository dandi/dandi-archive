from __future__ import annotations

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.db import transaction
import djclick as click
import faker

from dandiapi.api.models.user import UserMetadata


@click.command()
@click.option(
    '--auto-approve',
    is_flag=True,
    help='Auto approve this user, skipping the questionnaire.',
)
@click.option(
    '--password',
    default='password',
    show_default=True,
    help='The password for this user.',
)
def create_test_user(*, auto_approve: bool, password: str):
    fake = faker.Faker()

    with transaction.atomic():
        email = fake.email()
        user = User.objects.create(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            username=email,
            email=email,
        )

        user.set_password(password)
        user.save()

        UserMetadata.objects.create(
            user=user,
            status=UserMetadata.Status.APPROVED if auto_approve else UserMetadata.Status.INCOMPLETE,
        )

        uid = fake.random_number(digits=8, fix_len=True)
        SocialAccount.objects.create(
            user=user,
            provider='github',
            uid=uid,
            extra_data={
                'id': uid,
                'name': user.get_full_name(),
                'email': user.email,
                'login': fake.user_name(),
            },
        )

    click.echo(
        click.style(
            f'Created user "{user.email}" with password "{password}"',
            fg='green',
            bold=True,
        )
    )
