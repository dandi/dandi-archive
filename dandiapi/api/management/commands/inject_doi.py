from __future__ import annotations

from django.core.management.base import BaseCommand

from dandiapi.api.models import Dandiset, Version


class Command(BaseCommand):
    help = 'Inject a DOI into a dandiset version for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            'dandiset_identifier', type=str, help='Dandiset identifier (e.g., 000001)'
        )
        parser.add_argument(
            '--dandiset-version', type=str, default='draft', help='Version (default: draft)'
        )
        parser.add_argument(
            '--doi', type=str, help='DOI to inject (if not provided, will generate one)'
        )

    def handle(self, *args, **options):
        dandiset_identifier = options['dandiset_identifier']
        version = options['dandiset_version']
        doi = options['doi']

        try:
            try:
                dandiset = Dandiset.objects.get(id=int(dandiset_identifier))
            except (ValueError, Dandiset.DoesNotExist):
                numeric_id = (
                    int(dandiset_identifier.lstrip('0')) if dandiset_identifier.lstrip('0') else 0
                )
                dandiset = Dandiset.objects.get(id=numeric_id)

            version_obj = Version.objects.get(dandiset=dandiset, version=version)

            if not doi:
                # TODO: this prefix needs to be updated for non-dandi deployments
                doi = f'10.80507/dandi.{dandiset_identifier}'

            version_obj.metadata['doi'] = doi
            version_obj.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully injected DOI "{doi}" into {dandiset_identifier}/{version}'
                )
            )

        except Dandiset.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Dandiset {dandiset_identifier} not found'))
        except Version.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Version {version} not found for dandiset {dandiset_identifier}')
            )
