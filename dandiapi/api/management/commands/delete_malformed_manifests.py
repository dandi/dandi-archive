from __future__ import annotations

import logging

from django.core.files.storage import default_storage
import djclick as click
from tqdm import tqdm

from dandiapi.api.manifests import _manifests_path, all_manifest_filepaths
from dandiapi.api.models import Version
from dandiapi.api.storage import get_boto_client
from dandiapi.api.tasks import write_manifest_files

logger = logging.getLogger(__name__)


def list_files_in_manifest_directory(version: Version) -> list[str]:
    """List all files in the manifest directory for a version."""
    manifest_dir = _manifests_path(version)
    client = get_boto_client()

    # List objects with the manifest directory prefix
    paginator = client.get_paginator('list_objects_v2')
    pages = paginator.paginate(
        Bucket=default_storage.bucket_name, Prefix=manifest_dir + '/', Delimiter='/'
    )

    return [obj.get('Key', '') for page in pages for obj in page.get('Contents', [])]


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
    help='Show what would be deleted without actually deleting.',
)
def delete_malformed_manifests(dandisets: tuple[int, ...], *, include_all: bool, dry_run: bool):  # noqa: C901, PLR0912
    """
    Regenerate manifest files and clean up extra files.

    This command:
    1. Finds any versions with extra manifest files
    2. Regenerates the manifest files for the versions with extra files
    2. Deletes any junk files in the manifest directory
    """
    if bool(dandisets) == include_all:
        raise click.ClickException("Must specify exactly one of 'dandisets' or --all")

    # Build query for versions
    version_qs = Version.objects.filter(version='draft').select_related('dandiset')
    if dandisets:
        version_qs = version_qs.filter(dandiset_id__in=dandisets)

    total_versions = version_qs.count()
    click.echo('Scanning dandisets for extra manifest files...')

    # First pass: identify versions with extra files
    versions_with_extra_files = []
    for version_obj in tqdm(version_qs.iterator(), total=total_versions):
        # Get expected manifest file paths
        expected_manifest_paths = set(all_manifest_filepaths(version_obj))

        # List all files in the manifest directory
        all_files = list_files_in_manifest_directory(version_obj)

        # Identify extra files
        extra_files = [
            file_path for file_path in all_files if file_path not in expected_manifest_paths
        ]

        if extra_files:
            versions_with_extra_files.append((version_obj, extra_files))

    if not versions_with_extra_files:
        click.echo('No versions found with extra manifest files. Nothing to do.')
        return

    click.echo(f'Scanned {total_versions} dandisets for extra manifest files')

    click.echo(f'\nProcessing {len(versions_with_extra_files)} versions with extra files...')
    regenerated_count = 0
    deleted_count = 0
    for processed_count, (version_obj, extra_files) in enumerate(versions_with_extra_files, 1):
        click.echo(
            f'Processing dandiset {version_obj.dandiset.identifier} '
            f'({processed_count}/{len(versions_with_extra_files)})'
        )

        regenerated_count += 1
        if not dry_run:
            click.echo('  Regenerating manifest files...')
            write_manifest_files(version_obj.pk)
        else:
            click.echo('  [DRY RUN] Would regenerate manifest files...')

        if not dry_run:
            click.echo(f'  Deleting {len(extra_files)} extra files:')
        else:
            click.echo(f'  [DRY RUN] Would delete {len(extra_files)} extra files:')

        for file_path in extra_files:
            deleted_count += 1
            if not dry_run:
                try:
                    default_storage.delete(file_path)
                except Exception as e:  # noqa: BLE001
                    click.echo(f'    Error deleting {file_path}: {e}', err=True)
                    deleted_count -= 1

    if dry_run:
        click.echo(f'\n[DRY RUN] Would have regenerated {regenerated_count} manifest files')
        click.echo(f'[DRY RUN] Would have deleted {deleted_count} extra files')
    else:
        click.echo(f'\nRegenerated {regenerated_count} manifest files')
        click.echo(f'Deleted {deleted_count} extra files')
