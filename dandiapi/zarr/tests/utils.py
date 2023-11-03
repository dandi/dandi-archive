from __future__ import annotations

import hashlib
import os
from pathlib import Path

import faker
from zarr_checksum.generators import ZarrArchiveFile

from dandiapi.api.storage import get_boto_client
from dandiapi.zarr.models import ZarrArchive


def upload_zarr_file(zarr_archive: ZarrArchive, path: str | None = None, size: int = 100):
    if path is None:
        path = faker.Faker().file_path(absolute=False, extension='nwb')

    client = get_boto_client(zarr_archive.storage)
    data = os.urandom(size)
    client.put_object(
        Bucket=zarr_archive.storage.bucket_name, Key=zarr_archive.s3_path(path), Body=data
    )

    # Create ZarrArchiveFile
    h = hashlib.md5()
    h.update(data)
    return ZarrArchiveFile(path=Path(path), size=size, digest=h.hexdigest())
