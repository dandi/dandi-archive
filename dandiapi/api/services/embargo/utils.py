from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
from typing import TYPE_CHECKING

from botocore.config import Config
from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import Q
from more_itertools import chunked

from dandiapi.api.manifests import all_manifest_filepaths
from dandiapi.api.models.asset import Asset
from dandiapi.api.storage import get_boto_client
from dandiapi.zarr.models import zarr_s3_path

from .exceptions import AssetTagRemovalError

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

    from dandiapi.api.models.dandiset import Dandiset


logger = logging.getLogger(__name__)
TAG_REMOVAL_CHUNK_SIZE = 5000


def _delete_object_tags(blob: str):
    existing_tags: dict[str, str] = default_storage.get_tags(blob)
    filtered_tags = {key: val for key, val in existing_tags.items() if key != 'embargoed'}
    default_storage.put_tags(blob, filtered_tags)


def _delete_zarr_object_tags(client: S3Client, zarr: str):
    paginator = client.get_paginator('list_objects_v2')
    pages = paginator.paginate(
        Bucket=settings.DANDI_DANDISETS_BUCKET_NAME, Prefix=zarr_s3_path(zarr_id=zarr)
    )

    # Constant low thread number to limit memory usage, as each thread
    # creates its own boto client, consuming memory in the process
    with ThreadPoolExecutor(max_workers=4) as e:
        for page in pages:
            keys = [obj['Key'] for obj in page.get('Contents', [])]
            futures = [e.submit(_delete_object_tags, blob=key) for key in keys]

            # Check if any failed and raise exception if so
            failed = [key for i, key in enumerate(keys) if futures[i].exception() is not None]
            if failed:
                raise AssetTagRemovalError('Some zarr files failed to remove tags', blobs=failed)


def _remove_dandiset_manifest_tags(dandiset: Dandiset):
    version = dandiset.draft_version

    paths = all_manifest_filepaths(version)
    logger.info('Removing tags from dandiset %s', dandiset.identifier)
    for path in paths:
        try:
            existing_tags: dict[str, str] = default_storage.get_tags(path)
            filtered_tags = {key: val for key, val in existing_tags.items() if key != 'embargoed'}
            default_storage.put_tags(path, filtered_tags)
        except default_storage.s3_client.exceptions.NoSuchKey:
            logger.info('\tManifest file not found at %s. Continuing...', path)
            continue


def remove_dandiset_embargo_tags(dandiset: Dandiset):
    client = get_boto_client(config=Config(max_pool_connections=100))

    _remove_dandiset_manifest_tags(dandiset=dandiset)

    embargoed_assets = (
        Asset.objects.filter(versions__dandiset=dandiset)
        # zarrs have no embargoed flag themselves and so are all included
        .filter(Q(blob__embargoed=True) | Q(zarr__isnull=False))
        .values_list('blob__blob', 'zarr__zarr_id')
        .iterator(chunk_size=TAG_REMOVAL_CHUNK_SIZE)
    )

    # Chunk the blobs so we're never storing a list of all embargoed blobs
    chunks = chunked(embargoed_assets, TAG_REMOVAL_CHUNK_SIZE)
    for chunk in chunks:
        futures = []

        # Constant low thread number to limit memory usage, as each thread
        # creates its own boto client, consuming memory in the process
        with ThreadPoolExecutor(max_workers=4) as e:
            for blob, zarr in chunk:
                if blob is not None:
                    futures.append(e.submit(_delete_object_tags, blob=blob))
                if zarr is not None:
                    futures.append(e.submit(_delete_zarr_object_tags, client=client, zarr=zarr))

        # Check if any failed and raise exception if so
        failed = [blob for i, blob in enumerate(chunk) if futures[i].exception() is not None]
        if failed:
            raise AssetTagRemovalError('Some assets failed to remove tags', blobs=failed)
