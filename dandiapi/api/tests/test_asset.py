import json
import os.path
from uuid import uuid4

from django.conf import settings
from django.db.utils import IntegrityError
from django.urls import reverse
from guardian.shortcuts import assign_perm
import pytest
import requests
from rest_framework.test import APIClient

from dandiapi.api.models import Asset, AssetBlob, EmbargoedAssetBlob, Version
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.views.serializers import AssetFolderSerializer, AssetSerializer

from .fuzzy import HTTP_URL_RE, TIMESTAMP_RE, URN_RE, UTC_ISO_TIMESTAMP_RE, UUID_RE

# Model tests


@pytest.mark.django_db
def test_asset_no_blob_zarr():
    # An attribute error is thrown when it tries to access url fields on the missing foreign keys
    with pytest.raises(AttributeError):
        Asset().save()


@pytest.mark.django_db
def test_asset_blob_and_zarr(asset_blob, zarr_archive):
    # An integrity error is thrown by the constraint that both blob and zarr cannot both be defined
    with pytest.raises(IntegrityError):
        Asset(blob=asset_blob, zarr=zarr_archive).save()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'path,asset_paths,expected',
    [
        ('', ['foo', 'bar/baz'], {'folders': ['bar'], 'files': ['foo']}),
        # ('', ['/foo', '/bar/baz'], {'folders': ['bar'], 'files': ['foo']}),  # edge case
        ('/', ['/foo', '/bar/baz'], {'folders': ['bar'], 'files': ['foo']}),
        ('', ['foo/bar', 'foo/baz', 'foo/boo'], {'folders': ['foo'], 'files': []}),
        ('/', ['foo/bar', 'foo/baz', 'foo/boo'], {'folders': [], 'files': []}),  # Negative test
        ('////', ['/foo', '/bar/baz'], {'folders': [], 'files': []}),
        ('a', ['a/b', 'a/c/d'], {'folders': ['c'], 'files': ['b']}),
        ('a/', ['a/b', 'a/c/d'], {'folders': ['c'], 'files': ['b']}),
        ('/a', ['/a/b', '/a/c/d'], {'folders': ['c'], 'files': ['b']}),
        ('/a/', ['/a/b', '/a/c/d'], {'folders': ['c'], 'files': ['b']}),
    ],
)
def test_asset_rest_path(
    api_client,
    draft_version_factory,
    asset_factory,
    asset_blob_factory,
    path,
    asset_paths,
    expected,
):
    # Initialize version and contained assets
    asset_blob = asset_blob_factory()
    assets = [asset_factory(blob=asset_blob, path=p) for p in asset_paths]
    version: Version = draft_version_factory()
    for asset in assets:
        version.assets.add(asset)

    # Retrieve paths from endpointF
    paths = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/paths/',
        {'path_prefix': path},
    ).data

    # Ensure slash between path prefix and folders/files
    query_prefix = path
    if query_prefix and query_prefix[-1] != '/':
        query_prefix = f'{query_prefix}/'

    # Do folder assertions
    for folder_path in expected['folders']:
        assert folder_path in paths['results']['folders']

        folder_entry = paths['results']['folders'][folder_path]
        folder_assets = list(
            Asset.objects.all().filter(path__startswith=f'{query_prefix}{folder_path}')
        )
        serialized_folder = AssetFolderSerializer(
            {
                'created': min(asset.created for asset in folder_assets),
                'modified': max(asset.modified for asset in folder_assets),
                'size': sum(asset.size for asset in folder_assets),
                'num_files': len(folder_assets),
            }
        ).data

        assert folder_entry == serialized_folder

    # Do file assertions
    for file_path in expected['files']:
        assert file_path in paths['results']['files']

        asset: Asset = Asset.objects.get(path=f'{query_prefix}{file_path}')
        assert paths['results']['files'][file_path] == AssetSerializer(asset).data


@pytest.mark.django_db
@pytest.mark.parametrize(
    'path,asset_paths,page,expected_count,expected_results',
    [
        ('', ['a/b/c/d/e/f/g', 'foo', 'bar/baz'], 1, 3, {'folders': ['a'], 'files': []}),
        ('', ['a/b/c/d/e/f/g', 'foo', 'bar/baz'], 2, 3, {'folders': ['bar'], 'files': []}),
        ('', ['a/b/c/d/e/f/g', 'foo', 'bar/baz'], 3, 3, {'folders': [], 'files': ['foo']}),
    ],
)
def test_asset_rest_path_pagination(
    api_client: APIClient,
    draft_version_factory,
    asset_factory,
    asset_blob_factory,
    path: str,
    asset_paths: list,
    page: int,
    expected_count: int,
    expected_results: dict,
):
    # Initialize version and contained assets
    asset_blob = asset_blob_factory()
    assets = [asset_factory(blob=asset_blob, path=p) for p in asset_paths]
    version: Version = draft_version_factory()
    for asset in assets:
        version.assets.add(asset)

    # Retrieve paths from endpoint
    paths = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/paths/',
        {'path_prefix': path, 'page': page, 'page_size': 1},
    ).data

    assert paths.get('count') == expected_count

    assert (
        paths.get('previous') is None
        if page == 1
        else f'/api/dandisets/{version.dandiset.identifier}/versions'
        f'/draft/assets/paths/?page={page-1}&page_size=1'
    )

    assert (
        paths.get('next') is None
        if page == expected_count
        else f'/api/dandisets/{version.dandiset.identifier}/versions'
        f'/draft/assets/paths/?page={page+1}&page_size=1'
    )

    for item_type in ('files', 'folders'):
        assert len(paths['results'][item_type]) == len(expected_results[item_type])
        for name in paths['results']['folders']:
            assert name in expected_results['folders']


@pytest.mark.django_db
def test_asset_s3_url(asset_blob):
    signed_url = asset_blob.blob.url
    s3_url = asset_blob.s3_url
    assert signed_url.startswith(s3_url)
    assert signed_url.split('?')[0] == s3_url


@pytest.mark.django_db
def test_publish_asset(draft_asset: Asset):
    draft_asset_id = draft_asset.asset_id
    draft_blob = draft_asset.blob
    draft_metadata = draft_asset.metadata
    draft_asset.publish()
    draft_asset.save()

    # draft_asset has been published, so it is now published_asset
    published_asset = draft_asset

    assert published_asset.blob == draft_blob
    assert published_asset.metadata == {
        **draft_metadata,
        'id': f'dandiasset:{draft_asset_id}',
        'publishedBy': {
            'id': URN_RE,
            'name': 'DANDI publish',
            'startDate': UTC_ISO_TIMESTAMP_RE,
            'endDate': UTC_ISO_TIMESTAMP_RE,
            'wasAssociatedWith': [
                {
                    'id': URN_RE,
                    'identifier': 'RRID:SCR_017571',
                    'name': 'DANDI API',
                    # TODO version the API
                    'version': '0.1.0',
                    'schemaKey': 'Software',
                }
            ],
            'schemaKey': 'PublishActivity',
        },
        'datePublished': UTC_ISO_TIMESTAMP_RE,
        'identifier': str(draft_asset_id),
        'contentUrl': [HTTP_URL_RE, HTTP_URL_RE],
    }


@pytest.mark.django_db
def test_asset_total_size(
    draft_version_factory, asset_factory, asset_blob_factory, zarr_archive_factory
):
    # This asset blob should only be counted once,
    # despite belonging to multiple assets and multiple versions.
    asset_blob = asset_blob_factory()

    asset1 = asset_factory(blob=asset_blob)
    version1 = draft_version_factory()
    version1.assets.add(asset1)

    asset2 = asset_factory(blob=asset_blob)
    version2 = draft_version_factory()
    version2.assets.add(asset2)

    # These asset blobs should not be counted since they aren't in any versions.
    asset_blob_factory()
    asset_factory()

    assert Asset.total_size() == asset_blob.size

    zarr_archive = zarr_archive_factory()
    # give it some size
    zarr_archive.size = 100
    zarr_archive.save()  # save adjusted .size into DB

    # adding of an asset with zarr should be reflected
    asset3 = asset_factory(zarr=zarr_archive, blob=None)
    version2.assets.add(asset3)

    assert Asset.total_size() == asset_blob.size + zarr_archive.size

    # TODO: add testing for embargoed zar added, whenever embargoed zarrs
    # supported, ATM they are not and tested by test_zarr_rest_create_embargoed_dandiset


@pytest.mark.django_db
def test_asset_populate_metadata(draft_asset_factory):
    raw_metadata = {
        'foo': 'bar',
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
    }

    # This should trigger _populate_metadata to inject all the computed metadata fields
    asset = draft_asset_factory(metadata=raw_metadata)

    download_url = settings.DANDI_API_URL + reverse(
        'asset-download',
        kwargs={'asset_id': str(asset.asset_id)},
    )
    blob_url = asset.blob.s3_url
    assert asset.metadata == {
        **raw_metadata,
        'id': f'dandiasset:{asset.asset_id}',
        'path': asset.path,
        'identifier': str(asset.asset_id),
        'contentUrl': [download_url, blob_url],
        'contentSize': asset.blob.size,
        'digest': asset.blob.digest,
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',  # noqa: E501
    }


@pytest.mark.django_db
def test_asset_populate_metadata_zarr(draft_asset_factory, zarr_archive):
    raw_metadata = {
        'foo': 'bar',
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
    }

    # This should trigger _populate_metadata to inject all the computed metadata fields
    asset = draft_asset_factory(metadata=raw_metadata, blob=None, zarr=zarr_archive)

    download_url = settings.DANDI_API_URL + reverse(
        'asset-download',
        kwargs={'asset_id': str(asset.asset_id)},
    )
    s3_url = f'http://{settings.MINIO_STORAGE_ENDPOINT}/test-dandiapi-dandisets/test-prefix/test-zarr/{zarr_archive.zarr_id}/'  # noqa: E501
    assert asset.metadata == {
        **raw_metadata,
        'id': f'dandiasset:{asset.asset_id}',
        'path': asset.path,
        'identifier': str(asset.asset_id),
        'contentUrl': [download_url, s3_url],
        'contentSize': asset.size,
        'digest': asset.digest,
        # This should be injected on all zarr assets
        'encodingFormat': 'application/x-zarr',
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',  # noqa: E501
    }


# API Tests


@pytest.mark.django_db
def test_asset_rest_list(api_client, version, asset, asset_factory):
    version.assets.add(asset)

    # Create an extra asset so that there are multiple assets to filter down
    asset_factory()

    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/'
    ).json() == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'asset_id': str(asset.asset_id),
                'path': asset.path,
                'size': asset.size,
                'blob': asset.blob.blob_id,
                'zarr': None,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
            }
        ],
    }


@pytest.mark.parametrize(
    'path,result_indices',
    [
        ('foo.txt', [0]),
        ('bar.txt', [1]),
        ('foo', [0, 2]),
        ('bar', [1]),
        ('foo/', [2]),
        ('txt', []),
    ],
    ids=[
        'exact-match-foo',
        'exact-match-bar',
        'prefix-foo',
        'prefix-bar',
        'prefix-foo/',
        'no-match',
    ],
)
@pytest.mark.django_db
def test_asset_rest_list_path_filter(api_client, version, asset_factory, path, result_indices):
    assets = [
        asset_factory(path='foo.txt'),
        asset_factory(path='bar.txt'),
        asset_factory(path='foo/bar.txt'),
    ]
    for asset in assets:
        version.assets.add(asset)

    expected_assets = [assets[i] for i in result_indices]

    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
        data={'path': path},
    ).json() == {
        'count': len(expected_assets),
        'next': None,
        'previous': None,
        'results': [
            {
                'asset_id': str(asset.asset_id),
                'path': asset.path,
                'size': asset.size,
                'blob': asset.blob.blob_id,
                'zarr': None,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
            }
            for asset in expected_assets
        ],
    }


@pytest.mark.parametrize(
    'order_param,ordering',
    [
        ('created', ['b', 'a', 'c']),
        ('-created', ['c', 'a', 'b']),
        # Modified is same as created
        ('modified', ['b', 'a', 'c']),
        ('-modified', ['c', 'a', 'b']),
        ('path', ['a', 'b', 'c']),
        ('-path', ['c', 'b', 'a']),
    ],
    ids=['created', '-created', 'modified', '-modified', 'path', '-path'],
)
@pytest.mark.django_db
def test_asset_rest_list_ordering(api_client, version, asset_factory, order_param, ordering):
    # Create asset B first so that the path ordering is different from the created ordering.
    b = asset_factory(path='b')
    a = asset_factory(path='a')
    c = asset_factory(path='c')
    version.assets.add(a)
    version.assets.add(b)
    version.assets.add(c)

    results = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
        data={'order': order_param},
    ).data['results']

    # Summarize the returned asset objects with their path, so that we can parametrize the
    # expected results easier.
    result_paths = [asset['path'] for asset in results]
    assert result_paths == ordering


@pytest.mark.django_db
def test_asset_rest_retrieve(api_client, version, asset, asset_factory):
    version.assets.add(asset)

    # Create an extra asset so that there are multiple assets to filter down
    asset_factory()

    assert (
        api_client.get(
            f'/api/dandisets/{version.dandiset.identifier}/'
            f'versions/{version.version}/assets/{asset.asset_id}/'
        ).json()
        == asset.metadata
    )


@pytest.mark.django_db
def test_asset_rest_retrieve_no_sha256(api_client, version, asset):
    version.assets.add(asset)
    # Remove the sha256 from the factory asset
    asset.blob.sha256 = None
    asset.blob.save()

    assert (
        api_client.get(
            f'/api/dandisets/{version.dandiset.identifier}/'
            f'versions/{version.version}/assets/{asset.asset_id}/'
        ).json()
        == asset.metadata
    )


@pytest.mark.django_db
def test_asset_rest_info(api_client, version, asset):
    version.assets.add(asset)

    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.asset_id}/info/'
    ).json() == {
        'asset_id': str(asset.asset_id),
        'blob': str(asset.blob.blob_id),
        'zarr': None,
        'path': asset.path,
        'size': asset.size,
        'metadata': asset.metadata,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    'status,validation_error',
    [
        (Asset.Status.PENDING, ''),
        (Asset.Status.VALIDATING, ''),
        (Asset.Status.VALID, ''),
        (Asset.Status.INVALID, 'error'),
    ],
)
def test_asset_rest_validation(api_client, version, asset, status, validation_error):
    version.assets.add(asset)

    asset.status = status
    asset.validation_errors = validation_error
    asset.save()

    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.asset_id}/validation/'
    ).data == {
        'status': status,
        'validation_errors': validation_error,
    }


@pytest.mark.django_db
def test_asset_create(api_client, user, draft_version, asset_blob):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'encodingFormat': 'application/x-nwb',
        'path': path,
        'meta': 'data',
        'foo': ['bar', 'baz'],
        '1': 2,
    }

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/',
        {'metadata': metadata, 'blob_id': asset_blob.blob_id},
        format='json',
    ).json()
    new_asset = Asset.objects.get(asset_id=resp['asset_id'])
    assert resp == {
        'asset_id': UUID_RE,
        'path': path,
        'size': asset_blob.size,
        'blob': asset_blob.blob_id,
        'zarr': None,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'metadata': new_asset.metadata,
    }
    for key in metadata:
        assert resp['metadata'][key] == metadata[key]

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time

    # Adding an Asset should trigger a revalidation
    assert draft_version.status == Version.Status.PENDING


@pytest.mark.django_db
def test_asset_create_embargo(api_client, user, draft_version, embargoed_asset_blob):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'encodingFormat': 'application/x-nwb',
        'path': path,
        'meta': 'data',
        'foo': ['bar', 'baz'],
        '1': 2,
    }

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/',
        {'metadata': metadata, 'blob_id': embargoed_asset_blob.blob_id},
        format='json',
    ).json()
    new_asset = Asset.objects.get(asset_id=resp['asset_id'])
    assert resp == {
        'asset_id': UUID_RE,
        'path': path,
        'size': embargoed_asset_blob.size,
        'blob': embargoed_asset_blob.blob_id,
        'zarr': None,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'metadata': new_asset.metadata,
    }
    for key in metadata:
        assert resp['metadata'][key] == metadata[key]

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time

    # Adding an Asset should trigger a revalidation
    assert draft_version.status == Version.Status.PENDING


@pytest.mark.django_db
def test_asset_create_zarr(api_client, user, draft_version, zarr_archive):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'encodingFormat': 'application/x-zarr',
        'path': path,
        'meta': 'data',
        'foo': ['bar', 'baz'],
        '1': 2,
    }

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/',
        {'metadata': metadata, 'zarr_id': zarr_archive.zarr_id},
        format='json',
    ).json()
    new_asset = Asset.objects.get(asset_id=resp['asset_id'])
    assert resp == {
        'asset_id': UUID_RE,
        'path': path,
        'size': zarr_archive.size,
        'blob': None,
        'zarr': zarr_archive.zarr_id,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'metadata': new_asset.metadata,
    }
    for key in metadata:
        assert resp['metadata'][key] == metadata[key]

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time

    # Adding an Asset should trigger a revalidation
    assert draft_version.status == Version.Status.PENDING


@pytest.mark.django_db
def test_asset_create_zarr_wrong_dandiset(
    api_client, user, draft_version, zarr_archive_factory, dandiset_factory
):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    zarr_dandiset = dandiset_factory()
    zarr_archive = zarr_archive_factory(dandiset=zarr_dandiset)

    path = 'test/create/asset.txt'
    metadata = {
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'encodingFormat': 'application/x-zarr',
        'path': path,
        'meta': 'data',
        'foo': ['bar', 'baz'],
        '1': 2,
    }

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/',
        {'metadata': metadata, 'zarr_id': zarr_archive.zarr_id},
        format='json',
    )
    assert resp.status_code == 400
    assert resp.json() == ['The zarr archive belongs to a different dandiset']


@pytest.mark.django_db
def test_asset_create_no_blob_or_zarr(api_client, user, draft_version):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'encodingFormat': 'application/x-zarr',
        'path': path,
        'meta': 'data',
        'foo': ['bar', 'baz'],
        '1': 2,
    }

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/',
        {'metadata': metadata},
        format='json',
    )
    assert resp.status_code == 400
    assert resp.json() == {'blob_id': ['Exactly one of blob_id or zarr_id must be specified.']}


@pytest.mark.django_db
def test_asset_create_blob_and_zarr(api_client, user, draft_version, asset_blob, zarr_archive):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'encodingFormat': 'application/x-zarr',
        'path': path,
        'meta': 'data',
        'foo': ['bar', 'baz'],
        '1': 2,
    }

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/',
        {'metadata': metadata, 'blob_id': asset_blob.blob_id, 'zarr_id': zarr_archive.zarr_id},
        format='json',
    )
    assert resp.status_code == 400
    assert resp.json() == {'blob_id': ['Exactly one of blob_id or zarr_id must be specified.']}


@pytest.mark.django_db
def test_asset_create_no_valid_blob(api_client, user, draft_version):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {'path': path, 'foo': ['bar', 'baz'], '1': 2}
    uuid = uuid4()

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/',
        {'metadata': metadata, 'blob_id': uuid},
        format='json',
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_asset_create_no_path(api_client, user, draft_version, asset_blob):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    metadata = {'meta': 'data', 'foo': ['bar', 'baz'], '1': 2}

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/',
        {'metadata': metadata, 'blob_id': asset_blob.blob_id},
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == {'metadata': ['No path specified in metadata.']}


@pytest.mark.django_db
def test_asset_create_not_an_owner(api_client, user, version):
    api_client.force_authenticate(user=user)

    assert (
        api_client.post(
            f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
            {},
            format='json',
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_asset_create_published_version(api_client, user, published_version, asset):
    assign_perm('owner', user, published_version.dandiset)
    api_client.force_authenticate(user=user)
    published_version.assets.add(asset)

    resp = api_client.post(
        f'/api/dandisets/{published_version.dandiset.identifier}'
        f'/versions/{published_version.version}/assets/',
        {
            'metadata': asset.metadata,
            'blob_id': asset.blob.blob_id,
        },
        format='json',
    )
    assert resp.status_code == 405
    assert resp.data == 'Only draft versions can be modified.'


@pytest.mark.django_db
def test_asset_create_existing_path(api_client, user, draft_version, asset_blob, asset_factory):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
        'path': path,
        'meta': 'data',
        'foo': ['bar', 'baz'],
        '1': 2,
    }

    # Create an existing asset with a conflicting path
    existing_asset = asset_factory(path=path)
    draft_version.assets.add(existing_asset)

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/',
        {'metadata': metadata, 'blob_id': asset_blob.blob_id},
        format='json',
    )
    assert resp.status_code == 409


@pytest.mark.django_db
def test_asset_rest_update(api_client, user, draft_version, asset, asset_blob):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)
    draft_version.assets.add(asset)

    new_path = 'test/asset/rest/update.txt'
    new_metadata = {
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'encodingFormat': 'application/x-nwb',
        'path': new_path,
        'foo': 'bar',
        'num': 123,
        'list': ['a', 'b', 'c'],
    }

    resp = api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/'
        f'versions/{draft_version.version}/assets/{asset.asset_id}/',
        {'metadata': new_metadata, 'blob_id': asset_blob.blob_id},
        format='json',
    ).json()
    new_asset = Asset.objects.get(asset_id=resp['asset_id'])
    assert resp == {
        'asset_id': UUID_RE,
        'path': new_path,
        'size': asset_blob.size,
        'blob': asset_blob.blob_id,
        'zarr': None,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'metadata': new_asset.metadata,
    }
    for key in new_metadata:
        assert resp['metadata'][key] == new_metadata[key]

    # Updating an asset should leave it in the DB, but disconnect it from the version
    assert asset not in draft_version.assets.all()

    # A new asset should be created that is associated with the version
    new_asset = Asset.objects.get(asset_id=resp['asset_id'])
    assert new_asset in draft_version.assets.all()

    # The new asset should have a reference to the old asset
    assert new_asset.previous == asset

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time

    # Updating an Asset should trigger a revalidation
    assert draft_version.status == Version.Status.PENDING


@pytest.mark.django_db
def test_asset_rest_update_embargo(api_client, user, draft_version, asset, embargoed_asset_blob):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)
    draft_version.assets.add(asset)

    new_path = 'test/asset/rest/update.txt'
    new_metadata = {
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'encodingFormat': 'application/x-nwb',
        'path': new_path,
        'foo': 'bar',
        'num': 123,
        'list': ['a', 'b', 'c'],
    }

    resp = api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/'
        f'versions/{draft_version.version}/assets/{asset.asset_id}/',
        {'metadata': new_metadata, 'blob_id': embargoed_asset_blob.blob_id},
        format='json',
    ).json()
    new_asset = Asset.objects.get(asset_id=resp['asset_id'])
    assert resp == {
        'asset_id': UUID_RE,
        'path': new_path,
        'size': embargoed_asset_blob.size,
        'blob': embargoed_asset_blob.blob_id,
        'zarr': None,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'metadata': new_asset.metadata,
    }
    for key in new_metadata:
        assert resp['metadata'][key] == new_metadata[key]

    # Updating an asset should leave it in the DB, but disconnect it from the version
    assert asset not in draft_version.assets.all()

    # A new asset should be created that is associated with the version
    new_asset = Asset.objects.get(asset_id=resp['asset_id'])
    assert new_asset in draft_version.assets.all()

    # The new asset should have a reference to the old asset
    assert new_asset.previous == asset

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time

    # Updating an Asset should trigger a revalidation
    assert draft_version.status == Version.Status.PENDING


@pytest.mark.django_db
def test_asset_rest_update_zarr(api_client, user, draft_version, asset, zarr_archive):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)
    draft_version.assets.add(asset)

    new_path = 'test/asset/rest/update.txt'
    new_metadata = {
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'encodingFormat': 'application/x-zarr',
        'path': new_path,
        'foo': 'bar',
        'num': 123,
        'list': ['a', 'b', 'c'],
    }

    resp = api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/'
        f'versions/{draft_version.version}/assets/{asset.asset_id}/',
        {'metadata': new_metadata, 'zarr_id': zarr_archive.zarr_id},
        format='json',
    ).json()
    new_asset = Asset.objects.get(asset_id=resp['asset_id'])
    assert resp == {
        'asset_id': UUID_RE,
        'path': new_path,
        'size': zarr_archive.size,
        'blob': None,
        'zarr': zarr_archive.zarr_id,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'metadata': new_asset.metadata,
    }
    for key in new_metadata:
        assert resp['metadata'][key] == new_metadata[key]

    # Updating an asset should leave it in the DB, but disconnect it from the version
    assert asset not in draft_version.assets.all()

    # A new asset should be created that is associated with the version
    new_asset = Asset.objects.get(asset_id=resp['asset_id'])
    assert new_asset in draft_version.assets.all()

    # The new asset should have a reference to the old asset
    assert new_asset.previous == asset

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time

    # Updating an Asset should trigger a revalidation
    assert draft_version.status == Version.Status.PENDING


@pytest.mark.django_db
def test_asset_rest_update_unauthorized(api_client, draft_version, asset):
    draft_version.assets.add(asset)
    new_metadata = asset.metadata
    new_metadata['new_field'] = 'new_value'
    assert (
        api_client.put(
            f'/api/dandisets/{draft_version.dandiset.identifier}/'
            f'versions/{draft_version.version}/assets/{asset.asset_id}/',
            {'metadata': new_metadata},
            format='json',
        ).status_code
        == 401
    )


@pytest.mark.django_db
def test_asset_rest_update_not_an_owner(api_client, user, draft_version, asset):
    api_client.force_authenticate(user=user)
    draft_version.assets.add(asset)

    new_metadata = asset.metadata
    new_metadata['new_field'] = 'new_value'
    assert (
        api_client.put(
            f'/api/dandisets/{draft_version.dandiset.identifier}/'
            f'versions/{draft_version.version}/assets/{asset.asset_id}/',
            {'metadata': new_metadata},
            format='json',
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_asset_rest_update_published_version(api_client, user, published_version, asset):
    assign_perm('owner', user, published_version.dandiset)
    api_client.force_authenticate(user=user)
    published_version.assets.add(asset)

    new_metadata = asset.metadata
    new_metadata['new_field'] = 'new_value'
    resp = api_client.put(
        f'/api/dandisets/{published_version.dandiset.identifier}/'
        f'versions/{published_version.version}/assets/{asset.asset_id}/',
        {'metadata': new_metadata},
        format='json',
    )
    assert resp.status_code == 405
    assert resp.data == 'Only draft versions can be modified.'


@pytest.mark.django_db
def test_asset_rest_update_to_existing(api_client, user, draft_version, asset_factory):
    old_asset = asset_factory()
    existing_asset = asset_factory()
    draft_version.assets.add(old_asset)
    draft_version.assets.add(existing_asset)

    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    resp = api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/'
        f'versions/{draft_version.version}/assets/{old_asset.asset_id}/',
        {'metadata': existing_asset.metadata, 'blob_id': existing_asset.blob.blob_id},
        format='json',
    )
    assert resp.status_code == 409


@pytest.mark.django_db
def test_asset_rest_delete(api_client, user, draft_version, asset):
    api_client.force_authenticate(user=user)
    assign_perm('owner', user, draft_version.dandiset)
    draft_version.assets.add(asset)

    response = api_client.delete(
        f'/api/dandisets/{draft_version.dandiset.identifier}/'
        f'versions/{draft_version.version}/assets/{asset.asset_id}/'
    )
    assert response.status_code == 204

    assert asset not in draft_version.assets.all()
    assert asset in Asset.objects.all()

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time

    # Deleting an Asset should trigger a revalidation
    assert draft_version.status == Version.Status.PENDING


@pytest.mark.django_db
def test_asset_rest_delete_not_an_owner(api_client, user, version, asset):
    api_client.force_authenticate(user=user)
    version.assets.add(asset)

    response = api_client.delete(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.asset_id}/'
    )
    assert response.status_code == 403

    assert asset in Asset.objects.all()


@pytest.mark.django_db
def test_asset_rest_delete_published_version(api_client, user, published_version, asset):
    api_client.force_authenticate(user=user)
    assign_perm('owner', user, published_version.dandiset)
    published_version.assets.add(asset)

    response = api_client.delete(
        f'/api/dandisets/{published_version.dandiset.identifier}/'
        f'versions/{published_version.version}/assets/{asset.asset_id}/'
    )
    assert response.status_code == 405
    assert response.data == 'Only draft versions can be modified.'


@pytest.mark.django_db
def test_asset_download(api_client, storage, version, asset):
    # Pretend like AssetBlob was defined with the given storage
    AssetBlob.blob.field.storage = storage

    version.assets.add(asset)

    response = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.asset_id}/download/'
    )

    assert response.status_code == 302

    download_url = response.get('Location')
    assert download_url == HTTP_URL_RE

    download = requests.get(download_url)
    cd_header = download.headers.get('Content-Disposition')

    assert cd_header == f'attachment; filename="{os.path.basename(asset.path)}"'

    with asset.blob.blob.file.open('rb') as reader:
        assert download.content == reader.read()


@pytest.mark.django_db
def test_asset_download_embargo(
    authenticated_api_client,
    user,
    storage,
    draft_version_factory,
    dandiset_factory,
    asset_factory,
    embargoed_asset_blob_factory,
):
    # Pretend like EmbargoedAssetBlob was defined with the given storage
    EmbargoedAssetBlob.blob.field.storage = storage

    # Set draft version as embargoed
    version = draft_version_factory(
        dandiset=dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    )

    # Assign perms and set client
    assign_perm('owner', user, version.dandiset)
    client = authenticated_api_client

    # Generate assets and blobs
    embargoed_blob = embargoed_asset_blob_factory(dandiset=version.dandiset)
    asset = asset_factory(blob=None, embargoed_blob=embargoed_blob)
    version.assets.add(asset)

    response = client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.asset_id}/download/'
    )

    assert response.status_code == 302

    download_url = response.get('Location')
    assert download_url == HTTP_URL_RE

    download = requests.get(download_url)
    cd_header = download.headers.get('Content-Disposition')

    assert cd_header == f'attachment; filename="{os.path.basename(asset.path)}"'

    with asset.embargoed_blob.blob.file.open('rb') as reader:
        assert download.content == reader.read()


@pytest.mark.django_db
def test_asset_download_zarr(api_client, version, asset_factory, zarr_archive):
    asset = asset_factory(blob=None, zarr=zarr_archive)
    version.assets.add(asset)

    response = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.asset_id}/download/'
    )

    assert response.status_code == 302
    download_url = response.get('Location')
    assert download_url == f'/api/zarr/{zarr_archive.zarr_id}.zarr/'


@pytest.mark.django_db
def test_asset_direct_download(api_client, storage, version, asset):
    # Pretend like AssetBlob was defined with the given storage
    AssetBlob.blob.field.storage = storage

    version.assets.add(asset)

    response = api_client.get(f'/api/assets/{asset.asset_id}/download/')

    assert response.status_code == 302

    download_url = response.get('Location')
    assert download_url == HTTP_URL_RE

    download = requests.get(download_url)
    cd_header = download.headers.get('Content-Disposition')

    assert cd_header == f'attachment; filename="{os.path.basename(asset.path)}"'

    with asset.blob.blob.file.open('rb') as reader:
        assert download.content == reader.read()


@pytest.mark.django_db
def test_asset_direct_download_zarr(api_client, version, asset_factory, zarr_archive):
    asset = asset_factory(blob=None, zarr=zarr_archive)
    version.assets.add(asset)

    response = api_client.get(f'/api/assets/{asset.asset_id}/download/')

    assert response.status_code == 302
    download_url = response.get('Location')
    assert download_url == f'/api/zarr/{zarr_archive.zarr_id}.zarr/'


@pytest.mark.django_db
def test_asset_direct_download_head(api_client, storage, version, asset):
    # Pretend like AssetBlob was defined with the given storage
    AssetBlob.blob.field.storage = storage

    version.assets.add(asset)

    response = api_client.head(f'/api/assets/{asset.asset_id}/download/')

    assert response.status_code == 302

    download_url = response.get('Location')
    assert download_url == HTTP_URL_RE

    download = requests.get(download_url)
    cd_header = download.headers.get('Content-Disposition')

    assert cd_header == f'attachment; filename="{os.path.basename(asset.path)}"'

    with asset.blob.blob.file.open('rb') as reader:
        assert download.content == reader.read()


@pytest.mark.django_db
def test_asset_direct_metadata(api_client, asset):
    assert json.loads(api_client.get(f'/api/assets/{asset.asset_id}/').content) == asset.metadata


@pytest.mark.django_db
def test_asset_direct_info(api_client, asset):
    assert api_client.get(f'/api/assets/{asset.asset_id}/info/').json() == {
        'asset_id': str(asset.asset_id),
        'blob': str(asset.blob.blob_id),
        'zarr': None,
        'path': asset.path,
        'size': asset.size,
        'metadata': asset.metadata,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    'glob_pattern,expected_paths',
    [
        (
            '*.txt',
            ['a/b.txt', 'a/b/c.txt', 'a/b/c/d.txt', 'a/b/c/e.txt', 'a/b/d/e.txt'],
        ),
        (
            'a/b/c/*',
            ['a/b/c/d.txt', 'a/b/c/e.txt'],
        ),
        ('a/b/d/*', ['a/b/d/e.txt']),
    ],
)
def test_asset_rest_glob(api_client, asset_factory, version, glob_pattern, expected_paths):
    paths = ('a/b.txt', 'a/b/c.txt', 'a/b/c/d.txt', 'a/b/c/e.txt', 'a/b/d/e.txt')
    for path in paths:
        version.assets.add(asset_factory(path=path))

    resp = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
        {'glob': glob_pattern},
    )

    assert expected_paths == [asset['path'] for asset in resp.json()['results']]


@pytest.mark.django_db
@pytest.mark.parametrize(
    'regex_pattern,expected_paths',
    [
        (
            '[0-9].txt',
            ['1.txt', '1/2/3.txt'],
        ),
        (
            '[a-z].txt',
            ['a/b/c/d.txt', 'a/b/c/e.txt', 'a/b/d/e.txt'],
        ),
    ],
)
def test_asset_rest_regex_valid(api_client, asset_factory, version, regex_pattern, expected_paths):
    paths = ('1.txt', '1/2/3.txt', 'a/b/c/d.txt', 'a/b/c/e.txt', 'a/b/d/e.txt')
    for path in paths:
        version.assets.add(asset_factory(path=path))

    resp = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
        {'regex': regex_pattern},
    )

    assert expected_paths == [asset['path'] for asset in resp.json()['results']]


@pytest.mark.django_db
def test_asset_rest_regex_invalid(api_client, version):
    resp = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
        {'regex': '[[[[['},  # provide an invalid regex
    )

    assert resp.status_code == 400


@pytest.mark.django_db
def test_asset_rest_glob_regex_together(api_client, version):
    """Test that including both a glob and regex returns a 400 error."""
    resp = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
        {'regex': '[0-9].txt', 'glob': '*.txt'},
    )

    assert resp.status_code == 400
    assert resp.json() == {'glob': ['Cannot specify both glob and regex']}
