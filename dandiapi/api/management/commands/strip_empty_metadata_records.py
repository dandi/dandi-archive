from __future__ import annotations

import difflib

from django.db import transaction
import djclick as click
import yaml

from dandiapi.api.manifests import write_dandiset_jsonld, write_dandiset_yaml
from dandiapi.api.models import Version
from dandiapi.api.services import audit
from dandiapi.api.services.version.metadata import strip_empty_records


@click.command(
    help='Remove empty metadata records, such as {"schemaKey": "ContactPoint"}, from the '
    'draft versions of all Dandisets (`--all`) or of the given one, showing the changes as '
    'a diff. See https://github.com/dandi/dandi-archive/issues/2944'
)
@click.argument('dandiset', required=False)
@click.option('--all', 'apply_to_all', is_flag=True, help='Clean all draft versions.')
@click.option('--check', is_flag=True, help="Only show the changes, don't apply them.")
def strip_empty_metadata_records(*, dandiset: str | None, apply_to_all: bool, check: bool):
    if apply_to_all == (dandiset is not None):
        raise click.UsageError('Provide either `--all` or a `dandiset`.')

    vers = Version.objects.filter(version='draft').select_related('dandiset')
    if dandiset is not None:
        vers = vers.filter(dandiset=int(dandiset))

    affected = []
    for ver in vers.iterator():
        new_metadata = strip_empty_records(ver.metadata)
        if new_metadata != ver.metadata:
            affected.append(ver.id)
            click.echo(_yaml_diff(ver.metadata, new_metadata, str(ver)), nl=False)
    click.echo(f'Found {len(affected)} draft version(s) with empty metadata records')

    if not check:
        for version_id in affected:
            _strip_version(version_id)


def _yaml_diff(old: dict, new: dict, name: str) -> str:
    old_lines, new_lines = (
        yaml.safe_dump(m, sort_keys=False, allow_unicode=True).splitlines(keepends=True)
        for m in (old, new)
    )
    return ''.join(difflib.unified_diff(old_lines, new_lines, f'a/{name}', f'b/{name}'))


def _strip_version(version_id: int) -> None:
    with transaction.atomic():
        ver = Version.objects.select_for_update().select_related('dandiset').get(id=version_id)
        if ver.status == Version.Status.PUBLISHING:
            click.echo(f'Skipping {ver}, which is being published')
            return
        new_metadata = strip_empty_records(ver.metadata)
        if new_metadata == ver.metadata:
            return

        ver.metadata = new_metadata
        # A PUBLISHED draft stays identical to its published version, so keep its status
        # to not make it publishable again. Revalidate others, which rewrites manifests.
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
