from dandischema import migrate
from django.conf import settings
import djclick as click

from dandiapi.api.models import Version
from dandiapi.api.tasks import validate_version_metadata


@click.command()
@click.argument('to_version')
def migrate_version_metadata(to_version: str):
    print(f'Migrating all version metadata to version {to_version}')
    for version in Version.objects.filter(version='draft'):
        print(f'Migrating {version.dandiset.identifier}/{version.version}')

        metadata = version.metadata
        # If there is no schemaVersion, assume the most recent
        if 'schemaVersion' not in metadata:
            metadata['schemaVersion'] = settings.DANDI_SCHEMA_VERSION

        try:
            metanew = migrate(metadata, to_version=to_version, skip_validation=True)
        except Exception as e:
            print(f'Failed to migrate {version.dandiset.identifier}/{version.version}')
            print(e)
            continue

        if version.metadata != metanew:
            version.metadata = metanew
            version.status = Version.Status.PENDING
            version.save()
