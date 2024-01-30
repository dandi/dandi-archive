from __future__ import annotations

from difflib import ndiff
from pprint import pformat

from dandischema import migrate
import djclick as click

from dandiapi.api.models import Version
from dandiapi.api.tasks import write_manifest_files


@click.command()
@click.argument('dandiset')
@click.argument('published_version')
@click.argument('to_version')
def migrate_published_version_metadata(*, dandiset: str, published_version: str, to_version: str):
    click.echo(
        f'Migrating published version {dandiset}/{published_version} '
        f'metadata to version {to_version}'
    )
    version = Version.objects.exclude(version='draft').get(
        dandiset=dandiset, version=published_version
    )
    metadata = version.metadata

    try:
        metanew = migrate(metadata, to_version=to_version, skip_validation=False)
    except Exception as e:  # noqa: BLE001
        click.echo(f'Failed to migrate {dandiset}/{published_version}')
        click.echo(e)
        raise click.Abort from e

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
