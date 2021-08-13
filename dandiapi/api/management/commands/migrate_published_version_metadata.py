from pprint import pformat
from difflib import ndiff

from dandischema import migrate
from django.conf import settings
from django.db.models import Q
import djclick as click

from dandiapi.api.models import Version
from dandiapi.api.tasks import write_manifest_files


@click.command()
@click.argument('dandiset')
@click.argument('published_version')
def migrate_published_version_metadata(dandiset: str, published_version: str):
    click.echo(
        f'Migrating published version {dandiset}/{published_version} metadata to version {settings.DANDI_SCHEMA_VERSION}'
    )
    version = Version.objects.filter(~Q(version='draft')).get(
        dandiset=dandiset, version=published_version
    )
    metadata = version.metadata

    # If there is no schemaVersion, assume the most recent
    if 'schemaVersion' not in metadata:
        metadata['schemaVersion'] = settings.DANDI_SCHEMA_VERSION

    try:
        metanew = migrate(metadata, to_version=settings.DANDI_SCHEMA_VERSION, skip_validation=False)
    except Exception as e:
        click.echo(f'Failed to migrate {dandiset}/{published_version}')
        click.echo(e)
        raise click.Abort()

    if metadata == metanew:
        click.echo('No changes detected')
    else:
        click.echo('Diff of changes to be saved:')
        click.echo(
            ''.join(
                ndiff(
                    pformat(metadata).splitlines(keepends=True),
                    pformat(metanew).splitlines(keepends=True),
                )
            )
        )

        click.confirm('Do you want to save these changes?', abort=True)

        version.metadata = metanew
        version.save()

        write_manifest_files.delay(version.id)

        # We don't bother revalidating here because it's already published
