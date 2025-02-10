from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from django.db import transaction
import djclick as click

from dandiapi.api.models import Version
from dandiapi.api.tasks import write_manifest_files


@click.command(
    help='Correct corrupted metadata. If `--dandiset` and `--dandiset-version` are provided, '
    'apply the correction to the specified Dandiset version. Otherwise, apply the correction to '
    'all Dandiset versions.'
)
@click.option(
    '--dandiset',
    'dandiset',
    help='The Dandiset. (This must be provided if `--dandiset-version` is provided.)',
)
@click.option(
    '--dandiset-version',
    'dandiset_version',
    help='The version of the Dandiset. (This must be provided if `--dandiset` is provided.)',
)
def correct_metadata(*, dandiset: str | None, dandiset_version: str | None):
    # Func to use to correct the metadata (update as needed)
    correct_func: Callable[[dict], dict | None] = correct_affiliation_corruption

    # Ensure both options are provided together (or both omitted)
    if (dandiset is None) != (dandiset_version is None):
        raise click.UsageError(
            'Both `--dandiset` and `--dandiset-version` must be provided together.'
        )

    vers = (
        Version.objects.all()
        if dandiset is None
        else (Version.objects.get(dandiset=dandiset, version=dandiset_version),)
    )

    # List of changes to be applied to the database represented as tuples of the form
    # version to be changed and the new metadata
    changes: list[tuple[Version, dict]] = []
    for ver in vers:
        try:
            meta_corrected = correct_func(ver.metadata)
        except Exception as e:
            click.echo(
                f'{ver.dandiset.identifier}/{ver.version}: Failed to correct metadata with '
                f'`{correct_func.__name__}()`'
            )
            click.echo(e)
            raise click.Abort from e

        if meta_corrected is not None:
            changes.append((ver, meta_corrected))

    if changes:
        # Apply the changes to the database atomically
        with transaction.atomic():
            for ver, meta_corrected in changes:
                ver.metadata = meta_corrected
                ver.save()  # TODO: should I use `save()` in this case? It has some custom logic.

        for ver, _ in changes:
            write_manifest_files.delay(ver.id)  # TODO: Please check if this is needed

            click.echo(
                f'{ver.dandiset.identifier}/{ver.version}: Metadata corrected with '
                f'`{correct_func.__name__}()`'
            )
    else:
        click.echo(
            f'No changes. No metadata of the Dandiset version(s) need to be corrected per '
            f'`{correct_func.__name__}()`'
        )


def correct_affiliation_corruption(meta: dict) -> dict | None:
    """
    Correct corruptions in JSON objects with the `"schemaKey"` of `"Affiliation"`.

    :param meta: The Dandiset metadata instance potentially containing the objects to be corrected.
    :return: If there is correction to be made, return the corrected metadata; otherwise, return
        `None`.

    Note: This function corrects the corruptions described in
        https://github.com/dandi/dandi-schema/issues/276
    """
