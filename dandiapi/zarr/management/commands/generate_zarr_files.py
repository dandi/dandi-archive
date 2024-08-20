from __future__ import annotations

import binascii
import os
import uuid

import djclick as click
from more_itertools import chunked
from tqdm import tqdm

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveFile, ZarrArchiveVersion


def create_new_zarr_with_file_list(file_list: list[ZarrArchiveFile]):
    dandiset = Dandiset.objects.first()
    zarr = ZarrArchive.objects.create(
        dandiset=dandiset, name=binascii.hexlify(os.urandom(32)).decode()
    )
    zv = ZarrArchiveVersion.objects.create(zarr=zarr, version=uuid.uuid4())

    zarr_files = file_list.copy()
    for file in zarr_files:
        file.pk = None
        file.zarr_version = zv

    # Create in chunks to increase throughput
    CHUNK_SIZE = 5000
    chunks = list(chunked(zarr_files, CHUNK_SIZE))
    with tqdm(total=len(zarr_files)) as pbar:
        for chunk in chunks:
            ZarrArchiveFile.objects.bulk_create(chunk)
            pbar.update(CHUNK_SIZE)


@click.command()
def generate(*args, **kwargs):
    zarr = ZarrArchive.objects.get(versions__id=485)
    zv = zarr.versions.first()  # type: ignore
    file_list = list(zv.files.all())
    while ZarrArchiveFile.objects.count() < 1_000_000_000:  # noqa: PLR2004
        print('---', ZarrArchiveFile.objects.count())
        create_new_zarr_with_file_list(file_list=file_list)
