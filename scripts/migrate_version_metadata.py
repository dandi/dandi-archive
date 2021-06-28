from dandischema import migrate
from django.conf import settings

from dandiapi.api.models import Version, VersionMetadata
from dandiapi.api.tasks import validate_version_metadata


def run(to_version):
    print(f'Migrating all version metadata to version {to_version}')
    for version in Version.objects.filter(version='draft'):
        print(f'Migrating {version.dandiset.identifier}/{version.version}')

        metadata = version.metadata.metadata
        # If there is no schemaVersion, assume the most recent
        if 'schemaVersion' not in metadata:
            metadata['schemaVersion'] = settings.DANDI_SCHEMA_VERSION

        metanew = migrate(metadata, to_version=to_version, skip_validation=True)

        new: VersionMetadata
        new, created = VersionMetadata.objects.get_or_create(
            name=version.metadata.name,
            metadata=metanew,
        )
        if created:
            new.save()
        version.metadata = new
        version.save()

        validate_version_metadata.delay(version.id)
