from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
from typing import TYPE_CHECKING

from botocore.config import Config
from django.conf import settings
from django.db.models import Q
from more_itertools import chunked

from dandiapi.api.models.asset import Asset
from dandiapi.api.storage import get_boto_client
from dandiapi.zarr.models import zarr_s3_path

from .exceptions import AssetTagRemovalError

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

    from dandiapi.api.models.dandiset import Dandiset


logger = logging.getLogger(__name__)
TAG_REMOVAL_CHUNK_SIZE = 5000


def retry(times: int, exceptions: tuple[type[Exception]]):
    """
    Retry Decorator.

    Retries the wrapped function/method `times` times if the exceptions listed
    in ``exceptions`` are thrown

    :param times: The number of times to repeat the wrapped function/method
    :param exceptions: Lists of exceptions that trigger a retry attempt
    """

    def decorator(func):
        def newfn(*args, **kwargs):
            attempt = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    attempt += 1
            return func(*args, **kwargs)

        return newfn

    return decorator


@retry(times=3, exceptions=(Exception,))
def _delete_object_tags(client: S3Client, blob: str):
    client.delete_object_tagging(
        Bucket=settings.DANDI_DANDISETS_BUCKET_NAME,
        Key=blob,
    )


@retry(times=3, exceptions=(Exception,))
def _delete_zarr_object_tags(client: S3Client, zarr: str):
    paginator = client.get_paginator('list_objects_v2')
    pages = paginator.paginate(
        Bucket=settings.DANDI_DANDISETS_BUCKET_NAME, Prefix=zarr_s3_path(zarr_id=zarr)
    )

    with ThreadPoolExecutor(max_workers=100) as e:
        for page in pages:
            keys = [obj['Key'] for obj in page.get('Contents', [])]
            futures = [e.submit(_delete_object_tags, client=client, blob=key) for key in keys]

            # Check if any failed and raise exception if so
            failed = [key for i, key in enumerate(keys) if futures[i].exception() is not None]
            if failed:
                raise AssetTagRemovalError('Some zarr files failed to remove tags', blobs=failed)


def remove_dandiset_embargo_tags(dandiset: Dandiset):
    client = get_boto_client(config=Config(max_pool_connections=100))
    embargoed_assets = (
        Asset.objects.filter(versions__dandiset=dandiset)
        .filter(Q(blob__embargoed=True) | Q(zarr__embargoed=True))
        .values_list('blob__blob', 'zarr__zarr_id')
        .iterator(chunk_size=TAG_REMOVAL_CHUNK_SIZE)
    )

    # Chunk the blobs so we're never storing a list of all embargoed blobs
    chunks = chunked(embargoed_assets, TAG_REMOVAL_CHUNK_SIZE)
    for chunk in chunks:
        futures = []
        with ThreadPoolExecutor(max_workers=100) as e:
            for blob, zarr in chunk:
                if blob is not None:
                    futures.append(e.submit(_delete_object_tags, client=client, blob=blob))
                if zarr is not None:
                    futures.append(e.submit(_delete_zarr_object_tags, client=client, zarr=zarr))

        # Check if any failed and raise exception if so
        failed = [blob for i, blob in enumerate(chunk) if futures[i].exception() is not None]
        if failed:
            raise AssetTagRemovalError('Some assets failed to remove tags', blobs=failed)
