"""Management command to create a test dandiset with 20 owners to demonstrate the issue 1761."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from dandiapi.api.services.dandiset import create_dandiset
from dandiapi.api.services.permissions.dandiset import get_dandiset_owners, replace_dandiset_owners


class Command(BaseCommand):
    help = 'Create a test dandiset with 20 owners to demonstrate the issue in GitHub issue #1761'

    def handle(self, *args, **options):
        with transaction.atomic():
            # Create 20 test users with names
            test_users_data = [
                # First name, Last name pairs for realistic test data
                ('Alex', 'Johnson'),
                ('Jamie', 'Smith'),
                ('Taylor', 'Williams'),
                ('Morgan', 'Brown'),
                ('Casey', 'Jones'),
                ('Jordan', 'Miller'),
                ('Riley', 'Davis'),
                ('Avery', 'Garcia'),
                ('Quinn', 'Rodriguez'),
                ('Drew', 'Martinez'),
                ('Skyler', 'Anderson'),
                ('Charlie', 'Taylor'),
                ('Finley', 'Thomas'),
                ('Blake', 'Hernandez'),
                ('Emerson', 'Moore'),
                ('Dakota', 'Martin'),
                ('Hayden', 'Jackson'),
                ('Parker', 'Thompson'),
                ('Reese', 'White'),
                ('Rowan', 'Lopez'),
            ]

            users = []
            for i, (first_name, last_name) in enumerate(test_users_data, 1):
                user = User.objects.filter(username=f'testuser{i}').first()
                if user:
                    # Update existing user with name if needed
                    if not user.first_name or not user.last_name:
                        user.first_name = first_name
                        user.last_name = last_name
                        user.save()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Updated user testuser{i} with name {first_name} {last_name}'
                            )
                        )
                    else:
                        self.stdout.write(self.style.SUCCESS(f'User testuser{i} already exists'))
                else:
                    # Create new user with name
                    # Using a test password, S106 is ignored as this is a test utility
                    user = User.objects.create_user(
                        username=f'testuser{i}',
                        email=f'testuser{i}@example.com',
                        password='password123',  # noqa: S106
                        first_name=first_name,
                        last_name=last_name,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'Created user testuser{i} ({first_name} {last_name})')
                    )
                users.append(user)

            # Create a dandiset with the first user as owner
            owner = users[0]
            dandiset_name = 'Test Dandiset with Many Owners'
            version_metadata = {
                'name': dandiset_name,
                'description': 'A test dandiset with 20 owners',
                'license': ['spdx:CC0-1.0'],
                'contributor': [],
                'schemaVersion': settings.DANDI_SCHEMA_VERSION,
            }

            dandiset, version = create_dandiset(
                user=owner,
                embargo=False,
                version_name=dandiset_name,
                version_metadata=version_metadata,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created dandiset {dandiset.identifier} with owner {owner.username}'
                )
            )

            # Set all 20 users as owners
            replace_dandiset_owners(dandiset, users)
            self.stdout.write(
                self.style.SUCCESS(f'Added {len(users)} owners to dandiset {dandiset.identifier}')
            )

            # Verify the number of owners
            owners = get_dandiset_owners(dandiset)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Dandiset {dandiset.identifier} now has {owners.count()} owners:'
                )
            )
            for i, owner in enumerate(owners, 1):
                self.stdout.write(f'  {i}. {owner.username} ({owner.email})')

            self.stdout.write(
                self.style.SUCCESS(
                    f'\nTo view this dandiset, go to: http://localhost:8000/api/dandisets/{dandiset.identifier}/'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'To view this dandiset in the web interface: http://localhost:5173/dandiset/{dandiset.identifier}'
                )
            )
