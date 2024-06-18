from __future__ import annotations

import json
from uuid import uuid4

from django.conf import settings
from django.db.utils import IntegrityError
from django.urls import reverse
from guardian.shortcuts import assign_perm
import pytest
import requests

from dandiapi.api.asset_paths import add_asset_paths, extract_paths
from dandiapi.api.models import Asset, AssetBlob, Version
from dandiapi.api.models.asset_paths import AssetPath
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.services.asset import add_asset_to_version
from dandiapi.api.services.asset.exceptions import AssetPathConflictError
from dandiapi.api.services.publish import publish_asset
from dandiapi.api.tasks.scheduled import validate_pending_asset_metadata
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus
from dandiapi.zarr.tasks import ingest_zarr_archive

from .fuzzy import HTTP_URL_RE, TIMESTAMP_RE, URN_RE, UTC_ISO_TIMESTAMP_RE, UUID_RE

# Model tests


@pytest.mark.django_db()
def test_asset_no_blob_zarr(draft_asset_factory):
    asset = draft_asset_factory()

    # An integrity error is thrown when the blob/zarr check constraint fails
    asset.blob = None
    with pytest.raises(IntegrityError) as excinfo:
        asset.save()

    assert 'blob-xor-zarr' in str(excinfo.value)


@pytest.mark.django_db()
def test_asset_blob_and_zarr(draft_asset, zarr_archive):
    # An integrity error is thrown by the constraint that both blob and zarr cannot both be defined
    draft_asset.zarr = zarr_archive
    with pytest.raises(IntegrityError) as excinfo:
        draft_asset.save()

    assert 'blob-xor-zarr' in str(excinfo.value)


@pytest.mark.django_db()
def test_asset_rest_path(api_client, draft_version_factory, asset_factory):
    # Initialize version and contained assets
    version: Version = draft_version_factory()
    asset = asset_factory(path='foo/bar/baz/a.txt')
    version.assets.add(asset)

    # Add asset path
    add_asset_paths(asset, version)

    # Retrieve root paths
    resp = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/paths/',
        {'path_prefix': ''},
    ).data
    assert resp['count'] == 1
    val = resp['results'][0]
    assert val['aggregate_files'] == 1


@pytest.mark.django_db()
def test_asset_rest_path_not_found(api_client, draft_version_factory, asset_factory):
    # Initialize version and contained assets
    version: Version = draft_version_factory()
    asset = asset_factory(path='foo/a.txt')
    version.assets.add(asset)

    # Add asset path
    add_asset_paths(asset, version)

    # Retrieve root paths
    resp = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/paths/',
        {'path_prefix': 'bar'},
    )
    assert resp.status_code == 404
    assert resp.json() == {'detail': 'Specified path not found.'}


@pytest.mark.django_db()
def test_asset_s3_url(asset_blob):
    signed_url = asset_blob.blob.url
    s3_url = asset_blob.s3_url
    assert signed_url.startswith(s3_url)
    assert signed_url.split('?')[0] == s3_url


@pytest.mark.django_db()
def test_publish_asset(draft_asset: Asset):
    draft_asset_id = draft_asset.asset_id
    draft_blob = draft_asset.blob
    draft_metadata = draft_asset.full_metadata

    draft_asset.status = Asset.Status.VALID
    draft_asset.save()

    publish_asset(asset=draft_asset)

    # draft_asset has been published, so it is now published_asset
    published_asset = draft_asset
    published_asset.refresh_from_db()

    assert published_asset.blob == draft_blob
    assert published_asset.full_metadata == {
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
                    # TODO: version the API
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


@pytest.mark.django_db()
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

    # TODO: add testing for embargoed zarr added, whenever embargoed zarrs
    # supported, ATM they are not and tested by test_zarr_rest_create_embargoed_dandiset


@pytest.mark.django_db()
def test_asset_full_metadata(draft_asset_factory):
    raw_metadata = {
        'foo': 'bar',
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
    }
    asset: Asset = draft_asset_factory(metadata=raw_metadata)

    # Test that full_metadata includes the correct values
    download_url = settings.DANDI_API_URL + reverse(
        'asset-download',
        kwargs={'asset_id': str(asset.asset_id)},
    )
    blob_url = asset.blob.s3_url
    assert asset.full_metadata == {
        **raw_metadata,
        'id': f'dandiasset:{asset.asset_id}',
        'path': asset.path,
        'identifier': str(asset.asset_id),
        'contentUrl': [download_url, blob_url],
        'contentSize': asset.blob.size,
        'digest': asset.blob.digest,
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',
    }


@pytest.mark.django_db()
def test_asset_full_metadata_zarr(draft_asset_factory, zarr_archive):
    raw_metadata = {
        'foo': 'bar',
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
    }
    asset: Asset = draft_asset_factory(metadata=raw_metadata, blob=None, zarr=zarr_archive)

    # Test that full_metadata includes the correct values
    download_url = settings.DANDI_API_URL + reverse(
        'asset-download',
        kwargs={'asset_id': str(asset.asset_id)},
    )
    s3_url = asset.zarr.s3_url
    assert asset.full_metadata == {
        **raw_metadata,
        'id': f'dandiasset:{asset.asset_id}',
        'path': asset.path,
        'identifier': str(asset.asset_id),
        'contentUrl': [download_url, s3_url],
        'contentSize': asset.size,
        'digest': asset.digest,
        # This should be injected on all zarr assets
        'encodingFormat': 'application/x-zarr',
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',
    }


# API Tests


@pytest.mark.django_db()
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
                'blob': str(asset.blob.blob_id),
                'zarr': None,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
            }
        ],
    }


@pytest.mark.django_db()
def test_asset_rest_list_include_metadata(api_client, version, asset, asset_factory):
    version.assets.add(asset)

    # Create an extra asset so that there are multiple assets to filter down
    asset_factory()

    # Assert false has no effect
    r = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
        {'metadata': False},
    )
    assert 'metadata' not in r.json()['results'][0]

    # Test positive case
    r = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
        {'metadata': True},
    )
    assert r.json()['results'][0]['metadata'] == asset.full_metadata


@pytest.mark.parametrize(
    ('path', 'result_indices'),
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
@pytest.mark.django_db()
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
                'blob': str(asset.blob.blob_id),
                'zarr': None,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
            }
            for asset in expected_assets
        ],
    }


@pytest.mark.parametrize(
    ('order_param', 'ordering'),
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
@pytest.mark.django_db()
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


@pytest.mark.django_db()
def test_asset_path_ordering(api_client, version, asset_factory):
    # The default collation will ignore special characters, including slashes, on the first pass. If
    # there are ties, it uses these characters to break ties. This means that in the below example,
    # removing the slashes leads to a comparison of 'az' and 'aaz', which would obviously sort the
    # latter before the former. However, with the slashes, it's clear that 'a/z' should come before
    # 'aa/z'. This is fixed by changing the collation of the path field, and as such this test
    # serves as a regression test.
    a = asset_factory(path='a/z')
    b = asset_factory(path='aa/z')
    version.assets.add(a)
    version.assets.add(b)

    asset_listing = Asset.objects.filter(versions__in=[version]).order_by('path')
    assert asset_listing.count() == 2
    assert asset_listing[0].pk == a.pk
    assert asset_listing[1].pk == b.pk


@pytest.mark.django_db()
def test_asset_rest_retrieve(api_client, version, asset, asset_factory):
    version.assets.add(asset)

    # Create an extra asset so that there are multiple assets to filter down
    asset_factory()

    assert (
        api_client.get(
            f'/api/dandisets/{version.dandiset.identifier}/'
            f'versions/{version.version}/assets/{asset.asset_id}/'
        ).json()
        == asset.full_metadata
    )


@pytest.mark.django_db()
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
        == asset.full_metadata
    )


@pytest.mark.django_db()
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
        'metadata': asset.full_metadata,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
    }


@pytest.mark.django_db()
@pytest.mark.parametrize(
    ('status', 'validation_error'),
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


@pytest.mark.django_db()
def test_asset_create(api_client, user, draft_version, asset_blob):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
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
        'metadata': new_asset.full_metadata,
    }

    # Assert all provided metadata exists
    for key in metadata:
        assert resp['metadata'][key] == metadata[key]

    # Assert paths are properly ingested
    for subpath in extract_paths(path):
        obj = AssetPath.objects.get(version=draft_version, path=subpath)
        if subpath == path:
            assert obj.asset == new_asset
        else:
            assert obj.asset is None

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time

    # Adding an Asset should trigger a revalidation
    assert draft_version.status == Version.Status.PENDING


@pytest.mark.parametrize(
    ('path', 'expected_status_code'),
    [
        ('foo.txt', 200),
        ('/foo', 400),
        ('', 400),
        ('/', 400),
        ('./foo', 400),
        ('../foo', 400),
        ('foo/.', 400),
        ('foo/..', 400),
        ('foo/./bar', 400),
        ('foo/../bar', 400),
        ('foo//bar', 400),
        ('foo\0bar', 400),
        ('foo/.bar', 200),
    ],
)
@pytest.mark.django_db()
def test_asset_create_path_validation(
    api_client, user, draft_version, asset_blob, path, expected_status_code
):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    metadata = {
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'encodingFormat': 'application/x-nwb',
        'path': path,
    }

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/',
        {'metadata': metadata, 'blob_id': asset_blob.blob_id},
        format='json',
    )

    assert resp.status_code == expected_status_code, resp.data


@pytest.mark.django_db()
def test_asset_create_conflicting_path(api_client, user, draft_version, asset_blob):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    # Add first asset
    add_asset_to_version(
        user=user,
        version=draft_version,
        asset_blob=asset_blob,
        metadata={
            'path': 'foo/bar.txt',
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        },
    )

    # Add an asset that has a path which fully contains that of the first asset
    with pytest.raises(AssetPathConflictError):
        add_asset_to_version(
            user=user,
            version=draft_version,
            asset_blob=asset_blob,
            metadata={
                'path': 'foo/bar.txt/baz.txt',
                'schemaVersion': settings.DANDI_SCHEMA_VERSION,
            },
        )

    # Add an asset that's path is fully contained by the first asset
    with pytest.raises(AssetPathConflictError):
        add_asset_to_version(
            user=user,
            version=draft_version,
            asset_blob=asset_blob,
            metadata={
                'path': 'foo',
                'schemaVersion': settings.DANDI_SCHEMA_VERSION,
            },
        )


@pytest.mark.django_db()
def test_asset_create_embargo(
    api_client, user, draft_version_factory, dandiset_factory, embargoed_asset_blob
):
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    draft_version = draft_version_factory(dandiset=dandiset)

    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)
    assert draft_version.dandiset.embargo_status == Dandiset.EmbargoStatus.EMBARGOED

    path = 'test/create/asset.txt'
    metadata = {
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

    assert new_asset.blob.embargoed
    assert new_asset.zarr is None

    # Adding an Asset should trigger a revalidation
    assert draft_version.status == Version.Status.PENDING


@pytest.mark.django_db()
def test_asset_create_unembargoing(
    api_client, user, draft_version_factory, dandiset_factory, embargoed_asset_blob
):
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING)
    draft_version = draft_version_factory(dandiset=dandiset)

    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
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
    )

    assert resp.status_code == 400


@pytest.mark.django_db()
def test_asset_create_embargoed_asset_blob_open_dandiset(
    api_client, user, draft_version, embargoed_asset_blob, mocker
):
    # Ensure that creating an asset in an open dandiset that points to an embargoed asset blob
    # results in that asset blob being unembargoed
    assert draft_version.dandiset.embargo_status == Dandiset.EmbargoStatus.OPEN
    assert embargoed_asset_blob.embargoed

    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
        'encodingFormat': 'application/x-nwb',
        'path': path,
        'meta': 'data',
        'foo': ['bar', 'baz'],
        '1': 2,
    }

    # Mock this so we can check that it's been called later
    mocked_func = mocker.patch('dandiapi.api.services.embargo.remove_asset_blob_embargoed_tag')

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/',
        {'metadata': metadata, 'blob_id': embargoed_asset_blob.blob_id},
        format='json',
    ).json()
    new_asset = Asset.objects.get(asset_id=resp['asset_id'])

    assert new_asset.blob == embargoed_asset_blob
    assert not new_asset.blob.embargoed

    # We can't test that the tags were correctly removed in a testing env, but we can test that the
    # function which removes the tags was correctly invoked
    mocked_func.assert_called_once()

    # Adding an Asset should trigger a revalidation
    assert draft_version.status == Version.Status.PENDING


@pytest.mark.django_db()
def test_asset_create_zarr(api_client, user, draft_version, zarr_archive):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
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
        'metadata': new_asset.full_metadata,
    }
    for key in metadata:
        assert resp['metadata'][key] == metadata[key]

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time

    # Asset should be pending, since checksum isn't calculated
    assert new_asset.status == Asset.Status.PENDING

    # Adding an Asset should trigger a revalidation
    assert draft_version.status == Version.Status.PENDING


# Must use transaction=True to ensure `on_commit` funcs are called
@pytest.mark.django_db(transaction=True)
def test_asset_create_zarr_validated(
    api_client, user, draft_version, zarr_archive, zarr_file_factory
):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
        'encodingFormat': 'application/x-zarr',
        'schemaKey': 'Asset',
        'path': path,
        'meta': 'data',
        'foo': ['bar', 'baz'],
        '1': 2,
    }

    # Create asset
    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/',
        {'metadata': metadata, 'zarr_id': zarr_archive.zarr_id},
        format='json',
    ).json()
    asset1 = Asset.objects.get(asset_id=resp['asset_id'])

    # Create second asset that points to the same zarr
    metadata['1'] = 3
    metadata['path'] = 'test/create/asset2.txt'
    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/',
        {'metadata': metadata, 'zarr_id': zarr_archive.zarr_id},
        format='json',
    ).json()
    asset2 = Asset.objects.get(asset_id=resp['asset_id'])

    # Add zarr file and finalize
    zarr_file_factory(zarr_archive=zarr_archive)
    api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')

    validate_pending_asset_metadata()

    asset1.refresh_from_db()
    asset2.refresh_from_db()
    assert asset1.status == Asset.Status.VALID
    assert asset2.status == Asset.Status.VALID


@pytest.mark.django_db()
def test_asset_create_zarr_wrong_dandiset(
    api_client, user, draft_version, zarr_archive_factory, dandiset_factory
):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    zarr_dandiset = dandiset_factory()
    zarr_archive = zarr_archive_factory(dandiset=zarr_dandiset)

    path = 'test/create/asset.txt'
    metadata = {
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
    assert resp.json() == 'The zarr archive belongs to a different dandiset'


@pytest.mark.django_db()
def test_asset_create_no_blob_or_zarr(api_client, user, draft_version):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
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


@pytest.mark.django_db()
def test_asset_create_blob_and_zarr(api_client, user, draft_version, asset_blob, zarr_archive):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {
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


@pytest.mark.django_db()
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


@pytest.mark.django_db()
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
    assert resp.data == {'metadata': ['No path specified in metadata.']}, resp.data


@pytest.mark.django_db()
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


@pytest.mark.django_db()
def test_asset_create_published_version(api_client, user, published_version, asset):
    assign_perm('owner', user, published_version.dandiset)
    api_client.force_authenticate(user=user)
    published_version.assets.add(asset)

    # Set path so API request succeeds
    asset.metadata['path'] = asset.path
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


@pytest.mark.django_db()
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


@pytest.mark.django_db()
def test_asset_rest_rename(api_client, user, draft_version, asset_blob):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    # Create asset
    metadata = {'path': 'foo/bar', 'schemaVersion': settings.DANDI_SCHEMA_VERSION}
    asset = add_asset_to_version(
        user=user, version=draft_version, asset_blob=asset_blob, metadata=metadata
    )

    # Change path and make update request
    metadata['path'] = 'foo/bar2'
    resp = api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/versions/{draft_version.version}/'
        f'assets/{asset.asset_id}/',
        {'metadata': metadata, 'blob_id': asset.blob.blob_id},
        format='json',
    )

    # Ensure new asset with new path was created
    assert resp.status_code == 200
    assert resp.json()['path'] == metadata['path']
    assert resp.json()['asset_id'] != str(asset.asset_id)


@pytest.mark.django_db()
def test_asset_rest_update(api_client, user, draft_version, asset, asset_blob):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)
    draft_version.assets.add(asset)
    add_asset_paths(asset=asset, version=draft_version)

    old_path = asset.path
    new_path = 'test/asset/rest/update.txt'
    new_metadata = {
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
        'metadata': new_asset.full_metadata,
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

    # Ensure new path is ingested
    assert not AssetPath.objects.filter(path=old_path, version=draft_version).exists()
    assert AssetPath.objects.filter(path=new_path, version=draft_version).exists()

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time

    # Updating an Asset should trigger a revalidation
    assert draft_version.status == Version.Status.PENDING


@pytest.mark.django_db()
def test_asset_rest_update_embargo(api_client, user, draft_version, asset, embargoed_asset_blob):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)
    draft_version.assets.add(asset)
    add_asset_paths(asset=asset, version=draft_version)

    new_path = 'test/asset/rest/update.txt'
    new_metadata = {
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
        'metadata': new_asset.full_metadata,
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


@pytest.mark.django_db()
def test_asset_rest_update_unembargoing(
    api_client, user, draft_version_factory, asset, embargoed_asset_blob
):
    draft_version = draft_version_factory(
        dandiset__embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING
    )
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)
    draft_version.assets.add(asset)

    new_path = 'test/asset/rest/update.txt'
    new_metadata = {
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
    )
    assert resp.status_code == 400


@pytest.mark.django_db()
def test_asset_rest_update_zarr(
    api_client,
    user,
    draft_version,
    draft_asset_factory,
    zarr_archive,
    zarr_file_factory,
):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    asset = draft_asset_factory(blob=None, zarr=zarr_archive)
    draft_version.assets.add(asset)
    add_asset_paths(asset=asset, version=draft_version)

    # Upload file and perform ingest
    zarr_file_factory(zarr_archive=zarr_archive)
    ingest_zarr_archive(zarr_archive.zarr_id)
    zarr_archive.refresh_from_db()

    new_path = 'test/asset/rest/update.txt'
    new_metadata = {
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
        'zarr': str(zarr_archive.zarr_id),
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'metadata': new_asset.full_metadata,
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


@pytest.mark.django_db()
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


@pytest.mark.django_db()
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


@pytest.mark.django_db()
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


@pytest.mark.django_db()
def test_asset_rest_update_to_existing(api_client, user, draft_version, asset_factory):
    old_asset = asset_factory()
    existing_asset = asset_factory()
    draft_version.assets.add(old_asset)
    draft_version.assets.add(existing_asset)

    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    # Set path so API request succeeds
    existing_asset.metadata['path'] = existing_asset.path
    resp = api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/'
        f'versions/{draft_version.version}/assets/{old_asset.asset_id}/',
        {'metadata': existing_asset.metadata, 'blob_id': existing_asset.blob.blob_id},
        format='json',
    )
    assert resp.status_code == 409


@pytest.mark.django_db()
def test_asset_rest_delete(api_client, user, draft_version, asset):
    assign_perm('owner', user, draft_version.dandiset)
    draft_version.assets.add(asset)

    # Add paths
    add_asset_paths(asset, draft_version)

    # Make request
    api_client.force_authenticate(user=user)
    response = api_client.delete(
        f'/api/dandisets/{draft_version.dandiset.identifier}/'
        f'versions/{draft_version.version}/assets/{asset.asset_id}/'
    )
    assert response.status_code == 204

    assert asset not in draft_version.assets.all()
    assert asset in Asset.objects.all()

    # Check paths
    assert not AssetPath.objects.filter(path=asset.path, version=draft_version).exists()

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time

    # Deleting an Asset should trigger a revalidation
    assert draft_version.status == Version.Status.PENDING


@pytest.mark.django_db()
def test_asset_rest_delete_unembargoing(api_client, user, draft_version_factory, asset):
    draft_version = draft_version_factory(
        dandiset__embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING
    )
    assign_perm('owner', user, draft_version.dandiset)
    draft_version.assets.add(asset)

    # Make request
    api_client.force_authenticate(user=user)
    response = api_client.delete(
        f'/api/dandisets/{draft_version.dandiset.identifier}/'
        f'versions/{draft_version.version}/assets/{asset.asset_id}/'
    )
    assert response.status_code == 400


@pytest.mark.django_db()
def test_asset_rest_delete_zarr(
    api_client,
    user,
    draft_version,
    draft_asset_factory,
    zarr_archive,
    zarr_file_factory,
):
    asset = draft_asset_factory(blob=None, zarr=zarr_archive)
    assign_perm('owner', user, draft_version.dandiset)
    draft_version.assets.add(asset)

    # Add paths
    add_asset_paths(asset=asset, version=draft_version)

    # Upload zarr file and perform ingest
    zarr_file_factory(zarr_archive=zarr_archive)
    ingest_zarr_archive(zarr_archive.zarr_id)
    zarr_archive.refresh_from_db()

    # Delete
    api_client.force_authenticate(user=user)
    resp = api_client.delete(
        f'/api/dandisets/{draft_version.dandiset.identifier}/'
        f'versions/{draft_version.version}/assets/{asset.asset_id}/'
    )
    assert resp.status_code == 204


@pytest.mark.django_db()
def test_asset_rest_delete_zarr_modified(
    api_client,
    user,
    draft_version,
    zarr_archive_factory,
    zarr_file_factory,
    storage,
    monkeypatch,
):
    """Ensure that a zarr can be associated to an asset, modified, then the asset deleted."""
    # Pretend like our zarr was defined with the given storage
    monkeypatch.setattr(ZarrArchive, 'storage', storage)

    # Assign perms and authenticate user
    dandiset = draft_version.dandiset
    assign_perm('owner', user, dandiset)
    api_client.force_authenticate(user=user)

    # Ensure zarr is ingested
    zarr_archive = zarr_archive_factory(status=ZarrArchiveStatus.UPLOADED, dandiset=dandiset)
    zarr_file_factory(zarr_archive=zarr_archive, size=100)
    ingest_zarr_archive(zarr_archive.zarr_id)
    zarr_archive.refresh_from_db()

    # Create first asset, pointing to zarr
    resp = api_client.post(
        f'/api/dandisets/{dandiset.identifier}' f'/versions/{draft_version.version}/assets/',
        {
            'metadata': {
                'path': 'sample.zarr',
                'schemaVersion': settings.DANDI_SCHEMA_VERSION,
            },
            'zarr_id': zarr_archive.zarr_id,
        },
        format='json',
    ).json()

    asset = Asset.objects.get(asset_id=resp['asset_id'])
    assert asset.size == 100
    ap = AssetPath.objects.filter(version=draft_version, asset=asset).first()
    assert ap.aggregate_files == 1
    assert ap.aggregate_size == 100

    # Pretend to upload more data to the zarr
    resp = api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        ['foo/bar.txt'],
        format='json',
    )

    # Delete the asset
    resp = api_client.delete(
        f'/api/dandisets/{dandiset.identifier}/'
        f'versions/{draft_version.version}/assets/{asset.asset_id}/'
    )
    assert resp.status_code == 204


@pytest.mark.django_db()
def test_asset_rest_delete_not_an_owner(api_client, user, version, asset):
    api_client.force_authenticate(user=user)
    version.assets.add(asset)

    response = api_client.delete(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.asset_id}/'
    )
    assert response.status_code == 403

    assert asset in Asset.objects.all()


@pytest.mark.django_db()
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


@pytest.mark.django_db()
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

    download = requests.get(download_url, timeout=5)
    cd_header = download.headers.get('Content-Disposition')

    assert cd_header == f'attachment; filename="{asset.path.split("/")[-1]}"'

    with asset.blob.blob.file.open('rb') as reader:
        assert download.content == reader.read()


@pytest.mark.django_db()
def test_asset_download_embargo(
    authenticated_api_client,
    user,
    storage,
    draft_version_factory,
    dandiset_factory,
    asset_factory,
    embargoed_asset_blob,
    monkeypatch,
):
    # Pretend like AssetBlob was defined with the given storage
    monkeypatch.setattr(AssetBlob.blob.field, 'storage', storage)

    # Set draft version as embargoed
    version = draft_version_factory(
        dandiset=dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    )

    # Assign perms and set client
    assign_perm('owner', user, version.dandiset)
    client = authenticated_api_client

    # Generate assets and blobs
    asset = asset_factory(blob=embargoed_asset_blob)
    version.assets.add(asset)

    response = client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.asset_id}/download/'
    )

    assert response.status_code == 302

    download_url = response.get('Location')
    assert download_url == HTTP_URL_RE

    download = requests.get(download_url, timeout=5)
    cd_header = download.headers.get('Content-Disposition')

    assert cd_header == f'attachment; filename="{asset.path.split("/")[-1]}"'

    with asset.blob.blob.file.open('rb') as reader:
        assert download.content == reader.read()


@pytest.mark.django_db()
def test_asset_download_zarr(api_client, version, asset_factory, zarr_archive):
    asset = asset_factory(blob=None, zarr=zarr_archive)
    version.assets.add(asset)

    response = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.asset_id}/download/'
    )
    assert response.status_code == 400


@pytest.mark.django_db()
def test_asset_direct_download(api_client, storage, version, asset):
    # Pretend like AssetBlob was defined with the given storage
    AssetBlob.blob.field.storage = storage

    version.assets.add(asset)

    response = api_client.get(f'/api/assets/{asset.asset_id}/download/')

    assert response.status_code == 302

    download_url = response.get('Location')
    assert download_url == HTTP_URL_RE

    download = requests.get(download_url, timeout=5)
    cd_header = download.headers.get('Content-Disposition')

    assert cd_header == f'attachment; filename="{asset.path.split("/")[-1]}"'

    with asset.blob.blob.file.open('rb') as reader:
        assert download.content == reader.read()


@pytest.mark.django_db()
def test_asset_direct_download_zarr(api_client, version, asset_factory, zarr_archive):
    asset = asset_factory(blob=None, zarr=zarr_archive)
    version.assets.add(asset)

    response = api_client.get(f'/api/assets/{asset.asset_id}/download/')
    assert response.status_code == 400


@pytest.mark.django_db()
def test_asset_direct_download_head(api_client, storage, version, asset):
    # Pretend like AssetBlob was defined with the given storage
    AssetBlob.blob.field.storage = storage

    version.assets.add(asset)

    response = api_client.head(f'/api/assets/{asset.asset_id}/download/')

    assert response.status_code == 302

    download_url = response.get('Location')
    assert download_url == HTTP_URL_RE

    download = requests.get(download_url, timeout=5)
    cd_header = download.headers.get('Content-Disposition')

    assert cd_header == f'attachment; filename="{asset.path.split("/")[-1]}"'

    with asset.blob.blob.file.open('rb') as reader:
        assert download.content == reader.read()


@pytest.mark.django_db()
def test_asset_direct_metadata(api_client, asset):
    assert (
        json.loads(api_client.get(f'/api/assets/{asset.asset_id}/').content) == asset.full_metadata
    )


@pytest.mark.django_db()
def test_asset_direct_info(api_client, asset):
    assert api_client.get(f'/api/assets/{asset.asset_id}/info/').json() == {
        'asset_id': str(asset.asset_id),
        'blob': str(asset.blob.blob_id),
        'zarr': None,
        'path': asset.path,
        'size': asset.size,
        'metadata': asset.full_metadata,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
    }


@pytest.mark.django_db()
@pytest.mark.parametrize(
    ('glob_pattern', 'expected_paths'),
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
        ('*b*e.txt', ['a/b/c/e.txt', 'a/b/d/e.txt']),
        ('.*[a|b].txt', []),  # regexes shouldn't be evaluated
        ('a/b/c', []),
        ('a/b/c*', ['a/b/c.txt', 'a/b/c/d.txt', 'a/b/c/e.txt']),
        ('a/b/c.txt', ['a/b/c.txt']),
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

    # Sort both lists before comparing since ordering is not considered
    assert sorted(expected_paths) == sorted([asset['path'] for asset in resp.json()['results']])
