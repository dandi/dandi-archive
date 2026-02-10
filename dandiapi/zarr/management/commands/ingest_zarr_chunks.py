# ruff: noqa: T201
from __future__ import annotations

import uuid

import boto3
from django.contrib.auth.models import User
from django.db import transaction
import djclick as click
from tqdm import tqdm

from dandiapi.zarr.models import ZarrArchive, ZarrArchiveChunk, ZarrArchiveVersion

client = boto3.client('s3')


def get_zarr_files(zarr_id: uuid.UUID):
    # Use a dict to store only one version per key. This means only one
    # version is returned per key, which is intentional for an MVP
    files = []

    paginator = client.get_paginator('list_object_versions')
    page_iterator = paginator.paginate(Bucket='dandiarchive', Prefix=f'zarr/{zarr_id}/')
    for page in page_iterator:
        files.extend(obj for obj in page.get('Versions') if obj['IsLatest'])

    return files


def ingest_zarr_files(zarr_id: uuid.UUID, *, quiet: bool = False):
    try:
        zarr = ZarrArchive.objects.get(zarr_id=zarr_id)
    except ZarrArchive.DoesNotExist:
        raise click.ClickException(f'Zarr with zarr_id {zarr_id} does not exist') from None

    with transaction.atomic():
        version = ZarrArchiveVersion.objects.create(zarr=zarr, version_id=uuid.uuid4())
        if not quiet:
            print(f'Created Version {version.version_id}')

        common_prefix = zarr.s3_path('')
        zarr_files = [
            ZarrArchiveChunk(
                version=version,
                key=file['Key'].removeprefix(common_prefix),
                object_version_id=file['VersionId'],
                etag=file['ETag'].strip('"'),
                delete_marker=False,
            )
            for file in get_zarr_files(zarr_id=zarr_id)
        ]

        # Now create files
        if not quiet:
            print(f'Bulk creating {len(zarr_files)} zarr files')

        ZarrArchiveChunk.objects.bulk_create(zarr_files)

        if not quiet:
            print(f'Created {len(zarr_files)} zarr files')


@click.command()
@click.option('--zarr-id', 'zarr_id', type=click.UUID)
@click.option('--all', 'all_zarrs', is_flag=True)
def ingest_files(*, zarr_id: uuid.UUID | None, all_zarrs: bool):
    if (zarr_id is not None) == all_zarrs:
        raise click.ClickException('Must specify exactly one of --zarr-id or --all')

    user = User.objects.filter(is_superuser=True).first()
    if user is None:
        raise Exception('Must have defined superuser')  # noqa: TRY002

    if zarr_id is not None:
        ingest_zarr_files(zarr_id=zarr_id)

    # Only case remaining is --all

    # Filter out zarrs which already have an attached zarr version,
    # indicating that it was already ingested.
    zarrs = ZarrArchive.objects.filter(zarrarchiveversion__isnull=True)

    pbar = tqdm(zarrs)
    for zarr in pbar:
        pbar.set_description(str(zarr.zarr_id))
        ingest_zarr_files(zarr.zarr_id, quiet=True)
