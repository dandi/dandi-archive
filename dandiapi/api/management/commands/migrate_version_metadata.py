from dandischema import migrate
import djclick as click

from dandiapi.api.models import Version


@click.command()
@click.argument('to_version')
def migrate_version_metadata(to_version: str):
    click.echo(f'Migrating all version metadata to version {to_version}')
    for version in Version.objects.filter(version='draft'):
        click.echo(f'Migrating {version.dandiset.identifier}/{version.version}')

        metadata = version.metadata

        try:
            metanew = migrate(metadata, to_version=to_version, skip_validation=True)
        except Exception as e:
            click.echo(f'Failed to migrate {version.dandiset.identifier}/{version.version}')
            click.echo(e)
            continue

        if version.metadata != metanew:
            version.metadata = metanew
            version.status = Version.Status.PENDING
            version.save()
