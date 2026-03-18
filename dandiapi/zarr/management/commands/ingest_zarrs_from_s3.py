# ruff: noqa: T201
from __future__ import annotations

import logging
import uuid

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
import djclick as click
from zarr_checksum import compute_zarr_checksum
from zarr_checksum.generators import S3ClientOptions, yield_files_s3

from dandiapi.api.asset_paths import add_zarr_paths, delete_zarr_paths
from dandiapi.api.models.asset import Asset
from dandiapi.api.models.asset_paths import AssetPath
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.models.version import Version
from dandiapi.api.services.dandiset import create_open_dandiset
from dandiapi.zarr.models import (
    ZarrArchive,
    ZarrArchiveChunk,
    ZarrArchiveStatus,
    ZarrArchiveVersion,
)

logger = logging.getLogger(__name__)


def ingest_zarr_archive(zarr_id: str, *, force: bool = False):
    # Ensure zarr is in pending state before proceeding
    with transaction.atomic():
        zarr: ZarrArchive = ZarrArchive.objects.select_for_update().get(zarr_id=zarr_id)
        if not force and zarr.status != ZarrArchiveStatus.UPLOADED:
            logger.info('Zarrs must be in an UPLOADED state to begin ingestion. Exiting...')
            return

        # Set as ingesting
        zarr.status = ZarrArchiveStatus.INGESTING
        zarr.checksum = None
        zarr.save(update_fields=['status', 'checksum'])

    # Instantiate updater and add files as they come in.
    # Compute the checksum before starting the transaction to avoid long lived locks.
    logger.info('Computing checksum for zarr %s...', zarr.zarr_id)
    checksum = compute_zarr_checksum(
        yield_files_s3(
            bucket='dandiarchive',
            prefix=zarr.s3_path(''),
            client_options=S3ClientOptions(
                region_name=zarr.storage.region_name,
                use_ssl=zarr.storage.use_ssl,
                verify=zarr.storage.verify,
                endpoint_url=zarr.storage.endpoint_url,
                aws_access_key_id=zarr.storage.access_key,
                aws_secret_access_key=zarr.storage.secret_key,
                aws_session_token=zarr.storage.security_token,
                config=zarr.storage.client_config,
            ),
        )
    )
    # Zarr is in correct state, lock until ingestion finishes
    with transaction.atomic():
        zarr = (
            ZarrArchive.objects.select_related('dandiset')
            .select_for_update()
            .get(zarr_id=zarr_id, status=ZarrArchiveStatus.INGESTING)
        )

        # Remove all asset paths associated with this zarr before ingest
        delete_zarr_paths(zarr)

        # Set zarr fields
        zarr.checksum = checksum.digest
        zarr.file_count = checksum.count
        zarr.size = checksum.size
        zarr.status = ZarrArchiveStatus.COMPLETE
        zarr.save()

        # Add asset paths after ingest is finished
        add_zarr_paths(zarr)

        # Set version status back to PENDING, and update modified.
        Version.objects.filter(id=zarr.dandiset.draft_version.id).update(
            status=Version.Status.PENDING, modified=timezone.now()
        )


def get_default_dandiset():
    try:
        return Dandiset.objects.get(id=1)
    except Dandiset.DoesNotExist:
        pass

    user = User.objects.filter(is_superuser=True).first()
    if user is None:
        raise click.ClickException('Must have at least one superuser in the system')

    dandiset, _ = create_open_dandiset(
        user=user,
        identifier=1,
        version_name='Default Dandiset',
        version_metadata={},
    )

    return dandiset


def get_zarr_files(zarr: ZarrArchive) -> list:
    """List all current (latest) object versions under the given zarr's S3 prefix."""
    files = []

    paginator = zarr.storage.s3_client.get_paginator('list_object_versions')
    page_iterator = paginator.paginate(Bucket='dandiarchive', Prefix=zarr.s3_path(''))
    for page in page_iterator:
        files.extend(obj for obj in page.get('Versions', []) if obj['IsLatest'])

    return files


@transaction.atomic()
def ingest_zarr_files(zarr_id: uuid.UUID, *, quiet: bool = False):
    zarr = ZarrArchive.objects.create(
        zarr_id=zarr_id, name=str(zarr_id), dandiset=get_default_dandiset()
    )

    version = ZarrArchiveVersion.objects.create(zarr=zarr, version_id=uuid.uuid4())
    if not quiet:
        print(f'Created version {version.version_id} for zarr {zarr_id}')

    if not quiet:
        print('Listing files from S3..')

    common_prefix = zarr.s3_path('')
    zarr_files = [
        ZarrArchiveChunk(
            version=version,
            key=file['Key'].removeprefix(common_prefix),
            object_version_id=file['VersionId'],
            etag=file['ETag'].strip('"'),
            delete_marker=False,
        )
        for file in get_zarr_files(zarr=zarr)
    ]

    if not quiet:
        print(f'Bulk creating {len(zarr_files)} chunks')

    ZarrArchiveChunk.objects.bulk_create(zarr_files)

    if not quiet:
        print(f'Created {len(zarr_files)} chunks')


@click.command()
@click.argument('zarr_id', type=click.UUID)
@click.option('--force-recreate', is_flag=True)
def ingest_zarrs(*, zarr_id: uuid.UUID, force_recreate: bool):
    if force_recreate:
        AssetPath.objects.filter(asset__zarr__zarr_id=zarr_id).delete()
        Asset.objects.filter(zarr__zarr_id=zarr_id).delete()
        ZarrArchive.objects.filter(zarr_id=zarr_id).delete()

    ingest_zarr_files(zarr_id=zarr_id)

    ZarrArchive.objects.filter(zarr_id=zarr_id).update(status=ZarrArchiveStatus.UPLOADED)
    ingest_zarr_archive(zarr_id)

    zarr = ZarrArchive.objects.get(zarr_id=zarr_id)
    click.echo(f'Zarr {zarr_id} ingested with checksum {zarr.checksum}')
