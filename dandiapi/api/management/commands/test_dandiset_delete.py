import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

from dandiapi.api.models import Dandiset


class Command(BaseCommand):
    help = "Test dandiset deletion via REST API to verify DOI deletion behavior"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dandiset-id",
            type=str,
            required=True,
            help="Dandiset ID to delete (e.g., 000354)",
        )
        parser.add_argument(
            "--username",
            type=str,
            default="admin",
            help="Username to authenticate as (default: admin)",
        )
        parser.add_argument(
            "--base-url",
            type=str,
            default="http://localhost:8000",
            help="Base URL for the API (default: http://localhost:8000)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        dandiset_id = options["dandiset_id"]
        username = options["username"]
        base_url = options["base_url"].rstrip("/")
        dry_run = options["dry_run"]

        # Get the dandiset
        try:
            dandiset = Dandiset.objects.get(id=dandiset_id)
        except Dandiset.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Dandiset {dandiset_id} not found"))
            return

        self.stdout.write(f"Found dandiset: {dandiset.id}")
        self.stdout.write(f"Embargo status: {dandiset.embargo_status}")

        # Get draft version and check for DOI
        draft_version = dandiset.versions.filter(version='draft').first()
        if draft_version:
            self.stdout.write(f"Draft version exists")
            if draft_version.doi:
                self.stdout.write(f"Draft version has DOI: {draft_version.doi}")
            else:
                self.stdout.write("Draft version has no DOI")
        else:
            self.stdout.write("No draft version found")

        # Check for published versions
        published_versions = dandiset.versions.exclude(version='draft')
        if published_versions.exists():
            self.stderr.write(self.style.ERROR(
                f"Dandiset has {published_versions.count()} published versions. Cannot delete."
            ))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: Would delete dandiset via REST API"))
            return

        # Get user and create/get auth token
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User {username} not found"))
            return

        # Get or create auth token
        token, created = Token.objects.get_or_create(user=user)
        if created:
            self.stdout.write(f"Created new auth token for {username}")

        # Make the DELETE request
        delete_url = f"{base_url}/api/dandisets/{dandiset_id}/"
        headers = {
            "Authorization": f"Token {token.key}",
            "Content-Type": "application/json",
        }

        self.stdout.write(f"Making DELETE request to: {delete_url}")

        try:
            response = requests.delete(delete_url, headers=headers, timeout=30)

            if response.status_code == 204:
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully deleted dandiset {dandiset_id}"
                ))
                self.stdout.write("DOI deletion should have been triggered if DOI existed")
            elif response.status_code == 404:
                self.stderr.write(self.style.ERROR(f"Dandiset {dandiset_id} not found via API"))
            elif response.status_code == 403:
                self.stderr.write(self.style.ERROR(f"Permission denied - user {username} cannot delete this dandiset"))
            elif response.status_code == 400:
                self.stderr.write(self.style.ERROR(f"Bad request: {response.text}"))
            else:
                self.stderr.write(self.style.ERROR(
                    f"Unexpected response: {response.status_code} - {response.text}"
                ))
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Request failed: {e}"))

        # Verify deletion
        try:
            Dandiset.objects.get(id=dandiset_id)
            self.stderr.write(self.style.ERROR("Dandiset still exists after deletion attempt"))
        except Dandiset.DoesNotExist:
            self.stdout.write(self.style.SUCCESS("Confirmed: Dandiset no longer exists in database"))
