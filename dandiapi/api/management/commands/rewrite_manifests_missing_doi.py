from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from django.core.files.storage import default_storage
import djclick as click
from tqdm import tqdm
import yaml

from dandiapi.api.manifests import (
    _dandiset_jsonld_path,
    _dandiset_yaml_path,
    write_dandiset_jsonld,
    write_dandiset_yaml,
)
from dandiapi.api.models import Version

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from django.db.models import QuerySet

logger = logging.getLogger(__name__)


def _manifests_embedding_metadata(version: Version) -> Iterator[tuple[str, Callable[[Any], Any]]]:
    """Yield the manifest files written from `version.metadata`, with their parsers.

    These are the only manifests which embed the DOI; the asset and collection
    manifests are unaffected.
    """
    yield _dandiset_jsonld_path(version), json.load
    yield _dandiset_yaml_path(version), yaml.safe_load


def stale_manifest_paths(version: Version) -> list[str]:
    """Return the manifest paths of `version` which don't carry the DOI from its metadata.

    A manifest which is missing, unreadable, or malformed is also considered stale,
    since rewriting it is the fix in either case.
    """
    expected_doi = version.metadata.get('doi')

    stale = []
    for path, load in _manifests_embedding_metadata(version):
        try:
            with default_storage.open(path) as manifest_file:
                metadata = load(manifest_file)
            manifest_doi = metadata.get('doi')
        except Exception as e:  # noqa: BLE001
            logger.info('Could not read manifest %s, assuming it needs rewriting: %s', path, e)
            stale.append(path)
            continue

        if manifest_doi != expected_doi:
            stale.append(path)

    return stale


def _find_stale_versions(version_qs: QuerySet[Version]) -> list[tuple[Version, list[str]]]:
    """Return every published version in `version_qs` with its stale manifest paths."""
    total_versions = version_qs.count()
    click.echo(f'Scanning {total_versions} published versions for manifests missing their DOI...')

    stale_versions: list[tuple[Version, list[str]]] = []
    versions_without_doi = 0
    versions_with_unpopulated_doi: list[Version] = []
    for version in tqdm(version_qs.iterator(), total=total_versions):
        if not version.metadata.get('doi'):
            versions_without_doi += 1
            if version.doi:
                versions_with_unpopulated_doi.append(version)
            continue

        stale_paths = stale_manifest_paths(version)
        if stale_paths:
            stale_versions.append((version, stale_paths))

    if versions_without_doi:
        click.echo(f'\nSkipped {versions_without_doi} published versions with no DOI in metadata')
    for version in versions_with_unpopulated_doi:
        click.echo(
            f'  WARNING: {version.dandiset.identifier}/{version.version} has DOI {version.doi} '
            f'but no `doi` in its metadata, so its manifests cannot be repaired without '
            f'modifying the published version',
            err=True,
        )

    return stale_versions


@click.command()
@click.argument(
    'dandisets',
    type=click.INT,
    nargs=-1,
)
@click.option(
    '-a',
    '--all',
    'include_all',
    is_flag=True,
    help='Run on all dandisets.',
)
@click.option(
    '--dry-run',
    is_flag=True,
    default=False,
    help='Show what would be rewritten without writing anything.',
)
def rewrite_manifests_missing_doi(dandisets: tuple[int, ...], *, include_all: bool, dry_run: bool):
    """
    Rewrite the manifest files of published versions whose manifests are missing their DOI.

    Publishing used to mint the DOI and write the manifest files in a race condition,
    so the manifest could be written before the DOI was saved, leaving
    `dandiset.jsonld`/`dandiset.yaml` on S3 without `doi` (and with a non-DOI `citation`).
    See https://github.com/dandi/dandi-archive/issues/2759.

    This command rewrites the manifest files of versions who have a DOI stored in their metadata,
    but is missing from the existing manifest files in S3.

    Versions whose metadata itself has no `doi` are reported but skipped, as there is no DOI
    to write into their manifests.
    """
    if bool(dandisets) == include_all:
        raise click.ClickException("Must specify exactly one of 'dandisets' or --all")

    version_qs = (
        Version.objects.exclude(version='draft')
        .select_related('dandiset')
        .order_by('dandiset_id', 'version')
    )
    if dandisets:
        version_qs = version_qs.filter(dandiset_id__in=dandisets)

    stale_versions = _find_stale_versions(version_qs)
    if not stale_versions:
        click.echo('No published versions found with manifests missing their DOI. Nothing to do.')
        return

    click.echo(f'\nProcessing {len(stale_versions)} versions with stale manifests...')
    for processed_count, (version, stale_paths) in enumerate(stale_versions, 1):
        click.echo(
            f'Processing {version.dandiset.identifier}/{version.version} '
            f'({processed_count}/{len(stale_versions)})'
        )
        for path in stale_paths:
            click.echo(f'  Stale manifest: {path}')

        if dry_run:
            click.echo('  [DRY RUN] Would rewrite manifest files...')
        else:
            click.echo('  Rewriting manifest files...')
            write_dandiset_yaml(version)
            write_dandiset_jsonld(version)

    if dry_run:
        click.echo(
            f'\n[DRY RUN] Would have rewritten manifest files for {len(stale_versions)} versions'
        )
    else:
        click.echo(f'\nRewrote manifest files for {len(stale_versions)} versions')
