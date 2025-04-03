"""
Management command to create a test dandiset with 20 owners to demonstrate the
issue in https://github.com/dandi/dandi-archive/issues/1761
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from dandiapi.api.services.dandiset import create_dandiset
from dandiapi.api.services.permissions.dandiset import get_dandiset_owners, replace_dandiset_owners


class Command(BaseCommand):
    help = "Create a test dandiset with 20 owners to demonstrate the issue in GitHub issue #1761"

    def create_user(self, username, email, first_name, last_name, password):
        """Create a user if they don't exist already."""
        try:
            user = User.objects.get(username=username)
            # Update user with name if missing
            if not user.first_name or not user.last_name:
                user.first_name = first_name
                user.last_name = last_name
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Updated user {username} with name {first_name} {last_name}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"User {username} already exists"))
            return user
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            self.stdout.write(self.style.SUCCESS(f"Created user {username} ({first_name} {last_name})"))
            return user

    def handle(self, *args, **options):
        with transaction.atomic():
            # Create 20 test users
            users = []
            for i in range(1, 21):
                user = self.create_user(
                    username=f"testuser{i}",
                    email=f"testuser{i}@example.com",
                    password="password123"
                )
                users.append(user)
            
            # Create a dandiset with the first user as owner
            owner = users[0]
            dandiset_name = "Test Dandiset with Many Owners"
            version_metadata = {
                "name": dandiset_name,
                "description": "A test dandiset with 20 owners to demonstrate the issue in GitHub issue #1761",
                "license": ["spdx:CC0-1.0"],
                "contributor": [],
                "schemaVersion": settings.DANDI_SCHEMA_VERSION,
            }
            
            dandiset, version = create_dandiset(
                user=owner,
                embargo=False,
                version_name=dandiset_name,
                version_metadata=version_metadata
            )
            self.stdout.write(self.style.SUCCESS(
                f"Created dandiset {dandiset.identifier} with owner {owner.username}"
            ))
            
            # Set all 20 users as owners
            replace_dandiset_owners(dandiset, users)
            self.stdout.write(self.style.SUCCESS(
                f"Added {len(users)} owners to dandiset {dandiset.identifier}"
            ))
            
            # Verify the number of owners
            owners = get_dandiset_owners(dandiset)
            self.stdout.write(self.style.SUCCESS(
                f"Dandiset {dandiset.identifier} now has {owners.count()} owners:"
            ))
            for i, owner in enumerate(owners, 1):
                self.stdout.write(f"  {i}. {owner.username} ({owner.email})")
            
            self.stdout.write(self.style.SUCCESS(
                f"\nTo view this dandiset, go to: http://localhost:8000/api/dandisets/{dandiset.identifier}/"
            ))
            self.stdout.write(self.style.SUCCESS(
                f"To view this dandiset in the web interface: http://localhost:5173/dandiset/{dandiset.identifier}"
            ))
