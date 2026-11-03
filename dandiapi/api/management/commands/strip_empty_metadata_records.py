from __future__ import annotations

import typing

from django.db import transaction
import djclick as click

from dandiapi.api.manifests import write_dandiset_jsonld, write_dandiset_yaml
from dandiapi.api.models import Version
from dandiapi.api.services import audit
from dandiapi.api.services.version.metadata import strip_empty_records


@click.command(
    help='Remove nested metadata records which carry no information, such as '
    '{"schemaKey": "ContactPoint"}, from draft versions. If `--all` is provided, '
    'clean all draft versions. Otherwise, provide the Dandiset to clean. '
    'Published versions are never modified. '
    'See https://github.com/dandi/dandi-archive/issues/2944'
)
@click.argument('dandiset', required=False)
@click.option(
    '--all',
    'apply_to_all',
    is_flag=True,
    default=False,
    help='Clean all draft versions (cannot be combined with dandiset argument).',
)
@click.option(
    '--check',
    is_flag=True,
    help="Don't perform any changes, just list the draft versions which would be changed.",
)
def strip_empty_metadata_records(*, dandiset: str | None, apply_to_all: bool, check: bool):
    if apply_to_all:
        if dandiset is not None:
            raise click.UsageError('Cannot specify `--all` together with `dandiset` argument.')
    elif dandiset is None:
        raise click.UsageError('Either `--all` or `dandiset` argument must be provided.')

    vers = Version.objects.filter(version='draft').select_related('dandiset')
    if not apply_to_all:
        dandiset = typing.cast('str', dandiset)
        vers = vers.filter(dandiset=int(dandiset))

    affected = [
        (ver.id, str(ver))
        for ver in vers.iterator()
        if strip_empty_records(ver.metadata) != ver.metadata
    ]
    click.echo(f'Found {len(affected)} draft version(s) with empty metadata records')
    if check:
        for _, name in affected:
            click.echo(f'\t{name}')
        return

    for version_id, _ in affected:
        _strip_version(version_id)


def _strip_version(version_id: int) -> None:
    # Clean each version in its own transaction, locking it to not race with
    # concurrent metadata updates or validation.
    with transaction.atomic():
        ver = Version.objects.select_for_update().select_related('dandiset').get(id=version_id)
        if ver.status == Version.Status.PUBLISHING:
            click.echo(f'Skipping {ver}, which is being published')
            return

        new_meta = strip_empty_records(ver.metadata)
        if new_meta == ver.metadata:
            return

        ver.metadata = new_meta
        # A draft which is PUBLISHED is identical to its latest published version, and
        # removing empty records does not change that, so we keep the status to not make
        # it publishable again. Any other draft gets revalidated, which also writes its
        # manifests out again.
        published = ver.status == Version.Status.PUBLISHED
        if not published:
            ver.status = Version.Status.PENDING
        ver.save()

        audit.update_metadata(
            dandiset=ver.dandiset,
            metadata=ver.metadata,
            user=None,
            admin=True,
            description='Remove empty metadata records, see '
            'https://github.com/dandi/dandi-archive/issues/2944',
        )

    if published:
        write_dandiset_yaml(ver)
        write_dandiset_jsonld(ver)
    click.echo(f'Removed empty metadata records from {ver}')
