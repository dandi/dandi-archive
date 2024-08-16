from __future__ import annotations

import json
import uuid

import boto3
from django.contrib.auth.models import User
import djclick as click
import faker

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.services.dandiset import create_dandiset
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveFile, ZarrArchiveVersion

client = boto3.client('s3')


# zarrs = get_zarrs()
# for zarr_id in zarrs:
#     print(f'Processing zarr {zarr_id}')

#     zarr = ZarrArchive.objects.create(
#         dandiset=dandiset, zarr_id=uuid.UUID(zarr_id), name=faker.Faker().sentence()
#     )
#     files = get_zarr_files(zarr_id=zarr_id)

#     common_prefix = zarr.s3_path('')
#     version = ZarrArchiveVersion.objects.create(zarr=zarr, version=uuid.uuid4())

#     folders_set: set[str] = set()
#     folder_depths = {}
#     for file in files:
#         key = file['Key'].removeprefix(common_prefix)
#         nodepaths = extract_paths(key)[:-1]
#         folders_set |= set(nodepaths)

#         # Add depths
#         for i, path in enumerate(nodepaths):
#             if i not in folder_depths:
#                 folder_depths[i] = set()

#             folder_depths[i].add(path)

#     # Sort folders lexicographically
#     # folders = sorted(sorted(folders_set), key=str.upper)

#     depths = sorted(folder_depths.keys())
#     root_folder = ZarrArchiveFolder.objects.create(
#         zarr_version=version, parent=None, path='', root=True
#     )

#     # Maps paths to created zarr archive folders
#     folder_map = {'': root_folder}
#     for depth in depths:
#         paths = folder_depths[depth]
#         zarr_folders = [
#             ZarrArchiveFolder(
#                 zarr_version=version,
#                 parent=folder_map['/'.join(path.split('/')[:-1])],
#                 path=path,
#                 root=False,
#             )
#             for path in paths
#         ]

#         # Store in map
#         created = ZarrArchiveFolder.objects.bulk_create(zarr_folders)
#         for folder in created:
#             folder_map[folder.path] = folder

#     # Now create files
#     filtered_files = [
#         {
#             'Key': file['Key'].removeprefix(common_prefix),
#             'VersionId': file['VersionId'],
#             'ETag': file['ETag'].strip('"'),
#         }
#         for file in files
#     ]
#     zarr_files = [
#         ZarrArchiveFile(
#             zarr_version=version,
#             folder=folder_map[get_file_parent_path(file['Key'])],
#             path=file['Key'],
#             version_id=file['VersionId'],
#             etag=file['ETag'],
#         )
#         for file in filtered_files
#     ]
#     ZarrArchiveFile.objects.bulk_create(zarr_files)

#     print(f'Created {len(zarr_files)} zarr files')


def get_zarrs():
    zarrs = []

    options = {
        'Bucket': 'dandiarchive',
        'Prefix': 'zarr/',
        'Delimiter': '/',
    }
    while True:
        resp = client.list_objects_v2(**options)
        zarrs.extend(
            [obj['Prefix'].removeprefix('zarr/').strip('/') for obj in resp['CommonPrefixes']]
        )
        if not resp['IsTruncated']:
            break

        options['ContinuationToken'] = resp['NextContinuationToken']

    return zarrs


def get_zarr_files(zarr_id: str):
    # Use a dict to store only one version per key. This means only one
    # version is returned per key, which is intentional for an MVP
    files = {}

    options = {'Bucket': 'dandiarchive', 'Prefix': f'zarr/{zarr_id}/'}
    while True:
        resp = client.list_object_versions(**options)
        files.update({obj['Key']: obj for obj in resp['Versions']})
        if not resp['IsTruncated']:
            break

        options['VersionIdMarker'] = resp['NextVersionIdMarker']
        options['KeyMarker'] = resp['NextKeyMarker']

    return list(files.values())


def get_file_parent_path(path: str):
    return '/'.join(path.split('/')[:-1])


def read_zarr_metadata(
    key: str, version_id: str
) -> (
    tuple[dict, None, None]
    | tuple[None, dict, None]
    | tuple[None, None, dict]
    | tuple[None, None, None]
):
    zattrs = key.endswith('.zattrs')
    zarray = key.endswith('.zarray')
    zgroup = key.endswith('.zgroup')
    if not (zattrs or zarray or zgroup):
        return (None, None, None)

    print(f'Reading {key}...')
    resp = client.get_object(Bucket='dandiarchive', Key=key, VersionId=version_id)
    data = json.loads(resp['Body'].read().decode())

    return (
        data if zattrs else None,
        data if zarray else None,
        data if zgroup else None,
    )


@click.command()
def ingest_files(*args, **kwargs):
    user = User.objects.filter(is_superuser=True).first()
    if user is None:
        raise Exception('Must have defined superuser')  # noqa: TRY002

    dandiset = Dandiset.objects.first()
    if dandiset is None:
        dandiset, _ = create_dandiset(
            user=user, embargo=False, version_name='Test Dandiset', version_metadata={}
        )

    # Delete all and start fresh
    ZarrArchive.objects.all().delete()

    zarrs = get_zarrs()
    for zarr_id in zarrs:
        print(f'Processing zarr {zarr_id}')

        zarr = ZarrArchive.objects.create(
            dandiset=dandiset, zarr_id=uuid.UUID(zarr_id), name=faker.Faker().sentence()
        )
        files = get_zarr_files(zarr_id=zarr_id)

        common_prefix = zarr.s3_path('')
        version = ZarrArchiveVersion.objects.create(zarr=zarr, version=uuid.uuid4())

        zarr_files = []
        for file in files:
            zattrs, zarray, zgroup = read_zarr_metadata(
                key=file['Key'], version_id=file['VersionId']
            )

            zarr_files.append(
                ZarrArchiveFile(
                    zarr_version=version,
                    key=file['Key'].removeprefix(common_prefix),
                    version_id=file['VersionId'],
                    etag=file['ETag'].strip('"'),
                    zattrs=zattrs,
                    zarray=zarray,
                    zgroup=zgroup,
                )
            )

        # Now create files
        print(f'Bulk creating {len(zarr_files)} zarr files')
        ZarrArchiveFile.objects.bulk_create(zarr_files)
        print(f'Created {len(zarr_files)} zarr files')
