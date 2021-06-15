from dandischema import migrate

from dandiapi.api.models import Version, VersionMetadata


def run(to_version):
    print(f'Migrating all version metadata to version {to_version}')
    for version in Version.objects.all():
        print(f'Migrating {version.dandiset.identifier}/{version.version}')
        if not version.version == 'draft':
            continue
        metanew = migrate(version.metadata.metadata, to_version=to_version, skip_validation=True)
        new: VersionMetadata
        new, created = VersionMetadata.objects.get_or_create(
            name=version.metadata.name,
            metadata=metanew,
        )
        if created:
            new.save()
        version.metadata = new
        version.save()
