"""
Management command to check DOI health — find stuck or failed DOI states.

Run periodically (e.g., via cron or Celery beat) to detect DOIs that
are stuck in 'pending' or 'failed' state.
"""

from __future__ import annotations

import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from dandiapi.api.models import Version
from dandiapi.api.models.dandiset import Dandiset


class Command(BaseCommand):
    help = 'Check for DOIs stuck in pending or failed state.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold-minutes',
            type=int,
            default=30,
            help='Consider pending DOIs stuck after this many minutes (default: 30).',
        )

    def handle(self, *args, **options):
        threshold = timezone.now() - datetime.timedelta(minutes=options['threshold_minutes'])

        # Find versions stuck in 'pending' longer than threshold
        stuck_pending = Version.objects.filter(
            doi_state='pending',
            modified__lt=threshold,
        ).select_related('dandiset')

        # Find versions in 'failed' state
        failed = Version.objects.filter(
            doi_state='failed',
        ).select_related('dandiset')

        # Find dandisets without concept_doi
        missing_concept = Dandiset.objects.filter(
            concept_doi__isnull=True,
            embargo_status=Dandiset.EmbargoStatus.OPEN,
        )

        self.stdout.write('\n--- DOI Health Check ---')
        self.stdout.write(f'Threshold: {options["threshold_minutes"]} minutes\n')

        if stuck_pending.exists():
            self.stdout.write(
                self.style.WARNING(f'STUCK PENDING: {stuck_pending.count()} versions')
            )
            for v in stuck_pending[:20]:
                self.stdout.write(
                    f'  {v.dandiset.identifier}/{v.version} doi={v.doi} modified={v.modified}'
                )
        else:
            self.stdout.write(self.style.SUCCESS('No stuck pending DOIs'))

        if failed.exists():
            self.stdout.write(self.style.WARNING(f'FAILED: {failed.count()} versions'))
            for v in failed[:20]:
                self.stdout.write(
                    f'  {v.dandiset.identifier}/{v.version} doi={v.doi} modified={v.modified}'
                )
        else:
            self.stdout.write(self.style.SUCCESS('No failed DOIs'))

        if missing_concept.exists():
            self.stdout.write(
                self.style.WARNING(f'MISSING CONCEPT DOI: {missing_concept.count()} open dandisets')
            )
            for d in missing_concept[:20]:
                self.stdout.write(f'  {d.identifier}')
        else:
            self.stdout.write(self.style.SUCCESS('All open dandisets have concept DOIs'))

        total_issues = stuck_pending.count() + failed.count() + missing_concept.count()
        if total_issues > 0:
            self.stdout.write(self.style.ERROR(f'\nTotal issues: {total_issues}'))
        else:
            self.stdout.write(self.style.SUCCESS('\nAll DOIs healthy'))
