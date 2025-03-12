from __future__ import annotations

from copy import deepcopy
import sys
import typing
from typing import Any

from django.db import transaction
import djclick as click

from dandiapi.api.manifests import write_dandiset_jsonld, write_dandiset_yaml
from dandiapi.api.models import Version


@click.command(
    help='Correct corrupted metadata. If `--all` is provided, apply the correction to '
    'all Dandiset versions. Otherwise, provide the Dandiset to '
    'apply the correction to.'
)
@click.argument('dandiset', required=False)
@click.option(
    '--all',
    'apply_to_all',
    is_flag=True,
    default=False,
    help='Apply the correction to all Dandiset versions '
    '(cannot be combined with dandiset argument).',
)
@click.option(
    '--check',
    is_flag=True,
    help="Don't perform any changes, just check for corrupted metadata.",
)
def correct_metadata(  # noqa: C901
    *, dandiset: str | None, apply_to_all: bool, check: bool
):
    if apply_to_all:
        if dandiset is not None:
            raise click.UsageError('Cannot specify `--all` together with `dandiset` argument.')
    elif dandiset is None:
        raise click.UsageError('Either `--all` or `dandiset` argument must be provided.')

    # Get version queryset
    vers = Version.objects.all()
    if not apply_to_all:
        dandiset = typing.cast(str, dandiset)
        vers = vers.filter(dandiset=int(dandiset), version='draft')

    if not vers.exists():
        click.echo('No matching versions found')
        return

    # For each version, find and fix metadata corruptions, along with saving out manifest files
    for ver in vers:
        new_meta = correct_affiliation_corruption(ver.metadata)
        if new_meta is None:
            continue

        click.echo(f'Found corruption in {ver}')
        if check:
            continue

        # Save each version in a separate transaction to avoid de-sync with dandiset yaml/jsonld
        with transaction.atomic():
            write_dandiset_yaml(ver)
            write_dandiset_jsonld(ver)
            click.echo(f'\tWrote dandiset yaml and json for version {ver}')

            ver.metadata = new_meta
            ver.save()

    # Remaining check is not needed since no data was modified
    if check:
        return

    # If we find any un-fixed instances, raise exception
    remaining = [ver for ver in vers if correct_affiliation_corruption(ver.metadata) is not None]
    if remaining:
        click.echo(
            click.style(f'\nFound remaining corrupted versions: {remaining}', fg='red', bold=True)
        )
        sys.exit(1)


def correct_affiliation_corruption(meta: dict) -> dict | None:
    """
    Correct corruptions in JSON objects with the `"schemaKey"` of `"Affiliation"`.

    :param meta: The Dandiset metadata instance potentially containing the objects to be corrected.
    :return: If there is correction to be made, return the corrected metadata; otherwise, return
        `None`.

    Note: This function corrects the corruptions described in
        https://github.com/dandi/dandi-schema/issues/276
    """
    new_meta = deepcopy(meta)
    correct_objs(new_meta)

    return new_meta if new_meta != meta else None


def correct_objs(data: Any) -> None:
    if isinstance(data, dict):
        if 'schemaKey' in data and data['schemaKey'] == 'Affiliation':
            data.pop('contactPoint', None)
            data.pop('includeInCitation', None)
            data.pop('roleName', None)
        for value in data.values():
            correct_objs(value)
    elif isinstance(data, list):
        for item in data:
            correct_objs(item)
    else:
        return
