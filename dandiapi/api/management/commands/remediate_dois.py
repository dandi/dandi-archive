"""
Management command to remediate historical fake/null DOIs.

Finds published versions with missing, null, or fake DOIs and
registers correct DOIs on DataCite. Also backfills concept DOIs
for dandisets that don't have them.
"""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand

from dandiapi.api.models import Version
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.services.doi import create_dandiset_doi, create_published_version_doi
from dandiapi.api.services.doi.utils import doi_configured, format_doi
from dandiapi.api.tasks import write_manifest_files

logger = logging.getLogger(__name__)

FAKE_DOI_PATTERN = '.123456/0.123456.1234'


class Command(BaseCommand):
    help = 'Remediate published versions with fake/null DOIs and backfill concept DOIs.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would be remediated without making changes.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if not doi_configured():
            self.stderr.write('DOI settings are not configured. Aborting.')
            return

        if dry_run:
            self.stdout.write('=== DRY RUN — no changes will be made ===\n')

        # Phase 1: Fix published versions with fake or null DOIs
        self._remediate_version_dois(dry_run)

        # Phase 2: Backfill concept DOIs for dandisets
        self._backfill_concept_dois(dry_run)

        self.stdout.write('\nRemediation complete.')

    def _remediate_version_dois(self, dry_run: bool):
        """Find and fix published versions with bad DOIs."""
        self.stdout.write('\n--- Remediating version DOIs ---')

        # Find versions with null DOI
        null_doi_versions = Version.objects.filter(
            doi__isnull=True,
        ).exclude(version='draft')

        # Find versions with fake placeholder DOI
        fake_doi_versions = Version.objects.filter(
            doi__contains=FAKE_DOI_PATTERN,
        ).exclude(version='draft')

        affected = list(null_doi_versions) + list(fake_doi_versions)
        self.stdout.write(f'Found {len(affected)} versions with null or fake DOIs')

        for version in affected:
            real_doi = format_doi(version.dandiset.identifier, version.version)
            self.stdout.write(
                f'  {version.dandiset.identifier}/{version.version}: '
                f'{version.doi!r} -> {real_doi}'
            )

            if not dry_run:
                try:
                    version.metadata['doi'] = real_doi
                    version.doi = real_doi
                    version.doi_state = 'pending'
                    version.save()

                    create_published_version_doi(version)

                    version.doi_state = 'findable'
                    version.save(update_fields=['doi_state'])

                    # Regenerate manifests
                    write_manifest_files.delay(version.id)

                    self.stdout.write(f'    OK — DOI minted and manifests queued')
                except Exception as e:
                    version.doi_state = 'failed'
                    version.save(update_fields=['doi_state'])
                    self.stderr.write(f'    FAILED — {e}')

    def _backfill_concept_dois(self, dry_run: bool):
        """Backfill concept DOIs for dandisets that don't have them."""
        self.stdout.write('\n--- Backfilling concept DOIs ---')

        dandisets_without_concept_doi = Dandiset.objects.filter(concept_doi__isnull=True)
        self.stdout.write(
            f'Found {dandisets_without_concept_doi.count()} dandisets without concept DOI'
        )

        for dandiset in dandisets_without_concept_doi:
            concept_doi = format_doi(dandiset.identifier)
            has_published = dandiset.versions.exclude(version='draft').exists()

            self.stdout.write(
                f'  {dandiset.identifier}: concept_doi={concept_doi} '
                f'({"published" if has_published else "draft only"})'
            )

            if not dry_run:
                try:
                    dandiset.concept_doi = concept_doi
                    dandiset.save(update_fields=['concept_doi'])

                    # Set concept DOI on draft version too
                    draft = dandiset.versions.filter(version='draft').first()
                    if draft:
                        draft.doi = concept_doi
                        draft.save(update_fields=['doi'])

                    # Register on DataCite
                    create_dandiset_doi(dandiset)

                    self.stdout.write(f'    OK — Draft concept DOI registered')
                except Exception as e:
                    self.stderr.write(f'    FAILED — {e}')
