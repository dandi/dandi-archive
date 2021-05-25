import os.path
from uuid import uuid4

from django.conf import settings
from django.urls import reverse
from guardian.shortcuts import assign_perm
import pytest
import requests

from dandiapi.api.models import Asset, AssetBlob, Version
from dandiapi.api.views.serializers import AssetFolderSerializer, AssetSerializer

from .fuzzy import HTTP_URL_RE, TIMESTAMP_RE, URN_RE, UUID_RE

# Model tests


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
        assert folder_path in paths['folders']

        folder_entry = paths['folders'][folder_path]
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
        assert file_path in paths['files']

        asset: Asset = Asset.objects.get(path=f'{query_prefix}{file_path}')
        assert paths['files'][file_path] == AssetSerializer(asset).data


@pytest.mark.django_db
def test_asset_s3_url(asset_blob):
    signed_url = asset_blob.blob.url
    s3_url = asset_blob.s3_url
    assert signed_url.startswith(s3_url)
    assert signed_url.split('?')[0] == s3_url


@pytest.mark.django_db
def test_version_published_asset(asset):
    published_asset = Asset.published_asset(asset)
    published_asset.save()

    assert published_asset.blob == asset.blob
    assert published_asset.metadata.metadata == {
        **asset.metadata.metadata,
        'id': f'dandiasset:{published_asset.asset_id}',
        'publishedBy': {
            'id': URN_RE,
            'name': 'DANDI publish',
            'startDate': TIMESTAMP_RE,
            'endDate': TIMESTAMP_RE,
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
        'datePublished': TIMESTAMP_RE,
        'identifier': str(published_asset.asset_id),
        'contentUrl': [HTTP_URL_RE, HTTP_URL_RE],
    }


@pytest.mark.django_db
def test_asset_total_size(draft_version_factory, asset_factory, asset_blob_factory):
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


@pytest.mark.django_db
def test_asset_populate_metadata(asset_factory, asset_metadata):
    raw_metadata = asset_metadata.metadata

    # This should trigger _populate_metadata to inject all the computed metadata fields
    asset = asset_factory(metadata=asset_metadata)

    download_url = 'https://api.dandiarchive.org' + reverse(
        'asset-direct-download',
        kwargs={'asset_id': str(asset.asset_id)},
    )
    blob_url = asset.blob.s3_url
    assert asset.metadata.metadata == {
        **raw_metadata,
        'id': f'dandiasset:{asset.asset_id}',
        'path': asset.path,
        'identifier': str(asset.asset_id),
        'contentUrl': [download_url, blob_url],
        'contentSize': asset.blob.size,
        'digest': asset.blob.digest,
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',  # noqa: E501
    }


# API Tests


@pytest.mark.django_db
def test_asset_rest_list(api_client, version, asset):
    version.assets.add(asset)

    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/'
    ).data == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'asset_id': str(asset.asset_id),
                'path': asset.path,
                'size': asset.size,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
            }
        ],
    }


@pytest.mark.django_db
def test_asset_rest_retrieve(api_client, version, asset):
    version.assets.add(asset)

    assert (
        api_client.get(
            f'/api/dandisets/{version.dandiset.identifier}/'
            f'versions/{version.version}/assets/{asset.asset_id}/'
        ).data
        == asset.metadata.metadata
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
        ).data
        == asset.metadata.metadata
    )


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
    asset.validation_error = validation_error
    asset.save()

    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.asset_id}/validation/'
    ).data == {
        'status': status,
        'validation_error': validation_error,
    }


@pytest.mark.django_db
def test_asset_create(api_client, user, draft_version, asset_blob):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
        'schemaVersion': '0.4.4',
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
    ).data
    new_asset = Asset.objects.get(asset_id=resp['asset_id'])
    assert resp == {
        'asset_id': UUID_RE,
        'path': path,
        'size': asset_blob.size,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'metadata': new_asset.metadata.metadata,
    }
    for key in metadata:
        assert resp['metadata'][key] == metadata[key]

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time


@pytest.mark.django_db
def test_asset_create_no_valid_blob(api_client, user, draft_version):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    metadata = {'meta': 'data', 'foo': ['bar', 'baz'], '1': 2}
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
    assert resp.data == 'No path specified in metadata.'


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
            'metadata': asset.metadata.metadata,
            'blob_id': asset.blob.blob_id,
        },
        format='json',
    )
    assert resp.status_code == 405
    assert resp.data == 'Only draft versions can be modified.'


@pytest.mark.django_db
def test_asset_rest_update(api_client, user, draft_version, asset, asset_blob):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)
    draft_version.assets.add(asset)

    new_path = 'test/asset/rest/update.txt'
    new_metadata = {
        'schemaVersion': '0.4.4',
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
    ).data
    new_asset = Asset.objects.get(asset_id=resp['asset_id'])
    assert resp == {
        'asset_id': UUID_RE,
        'path': new_path,
        'size': asset_blob.size,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'metadata': new_asset.metadata.metadata,
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
        {'metadata': existing_asset.metadata.metadata, 'blob_id': existing_asset.blob.blob_id},
        format='json',
    ).data

    # Updating an Asset to be the same as an existing Asset should still mint a new Asset
    assert resp['asset_id'] != existing_asset.asset_id


@pytest.mark.django_db
def test_asset_rest_update_unauthorized(api_client, draft_version, asset):
    draft_version.assets.add(asset)
    new_metadata = asset.metadata.metadata
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

    new_metadata = asset.metadata.metadata
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

    new_metadata = asset.metadata.metadata
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
