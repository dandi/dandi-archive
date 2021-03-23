from uuid import uuid4

from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api.models import Asset

from .fuzzy import HTTP_URL_RE, TIMESTAMP_RE, UUID_RE

# Model tests


@pytest.mark.django_db
@pytest.mark.parametrize(
    'path,qs,expected',
    [
        ('', [{'path': '/foo'}, {'path': '/bar/baz'}], ['bar/', 'foo']),
        ('/', [{'path': '/foo'}, {'path': '/bar/baz'}], ['bar/', 'foo']),
        ('////', [{'path': '/foo'}, {'path': '/bar/baz'}], ['bar/', 'foo']),
        ('a', [{'path': '/a/b'}, {'path': '/a/c/d'}], ['b', 'c/']),
        ('a/', [{'path': '/a/b'}, {'path': '/a/c/d'}], ['b', 'c/']),
        ('/a', [{'path': '/a/b'}, {'path': '/a/c/d'}], ['b', 'c/']),
        ('/a/', [{'path': '/a/b'}, {'path': '/a/c/d'}], ['b', 'c/']),
        ('a', [{'path': 'a/b'}, {'path': 'a/c/d'}], ['b', 'c/']),
        ('a', [{'path': 'a/b/'}, {'path': 'a/c/d/'}], ['b', 'c/']),
        ('a', [{'path': '/a/b/'}, {'path': '/a/c/d/'}], ['b', 'c/']),
    ],
)
def test_asset_get_path(path, qs, expected):
    assert expected == Asset.get_path(path, qs)


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
                'uuid': str(asset.uuid),
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

    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.uuid}/'
    ).data == {
        **asset.metadata.metadata,
        'identifier': str(asset.uuid),
        'contentUrl': [
            f'https://api.dandiarchive.org/api/dandisets/{version.dandiset.identifier}'
            f'/versions/{version.version}/assets/{asset.uuid}/download/',
            HTTP_URL_RE,
        ],
    }


@pytest.mark.django_db
def test_asset_create(api_client, user, version, asset_blob):
    assign_perm('owner', user, version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/asset.txt'
    metadata = {'path': path, 'meta': 'data', 'foo': ['bar', 'baz'], '1': 2}

    assert api_client.post(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
        {'metadata': metadata, 'blob_id': asset_blob.blob_id},
        format='json',
    ).data == {
        'uuid': UUID_RE,
        'path': path,
        'size': asset_blob.size,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'metadata': metadata,
    }

    asset = Asset.objects.get(blob__sha256=asset_blob.sha256, versions=version)
    assert asset.metadata.metadata == metadata


@pytest.mark.django_db
def test_asset_create_no_valid_blob(api_client, user, version):
    assign_perm('owner', user, version.dandiset)
    api_client.force_authenticate(user=user)

    metadata = {'meta': 'data', 'foo': ['bar', 'baz'], '1': 2}
    uuid = uuid4()

    resp = api_client.post(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
        {'metadata': metadata, 'blob_id': uuid},
        format='json',
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_asset_create_no_path(api_client, user, version, asset_blob):
    assign_perm('owner', user, version.dandiset)
    api_client.force_authenticate(user=user)

    metadata = {'meta': 'data', 'foo': ['bar', 'baz'], '1': 2}

    resp = api_client.post(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
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
def test_asset_create_duplicate(api_client, user, version, asset):
    assign_perm('owner', user, version.dandiset)
    api_client.force_authenticate(user=user)
    version.assets.add(asset)

    resp = api_client.post(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
        {
            'metadata': asset.metadata.metadata,
            'blob_id': asset.blob.blob_id,
        },
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == 'Asset already exists.'


@pytest.mark.django_db
def test_asset_rest_update(api_client, user, version, asset, asset_blob):
    assign_perm('owner', user, version.dandiset)
    api_client.force_authenticate(user=user)
    version.assets.add(asset)

    new_path = 'test/asset/rest/update.txt'
    new_metadata = {'path': new_path, 'foo': 'bar', 'num': 123, 'list': ['a', 'b', 'c']}

    resp = api_client.put(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.uuid}/',
        {'metadata': new_metadata, 'blob_id': asset_blob.blob_id},
        format='json',
    ).data
    assert resp == {
        'uuid': UUID_RE,
        'path': new_path,
        'size': asset_blob.size,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'metadata': new_metadata,
    }

    # Updating an asset should leave it in the DB, but disconnect it from the version
    assert asset not in version.assets.all()

    # A new asset should be created that is associated with the version
    new_asset = Asset.objects.get(uuid=resp['uuid'])
    assert new_asset in version.assets.all()

    # The new asset should have a reference to the old asset
    assert new_asset.previous == asset


@pytest.mark.django_db
def test_asset_rest_update_to_existing(api_client, user, version, asset_factory):
    old_asset = asset_factory()
    existing_asset = asset_factory()
    version.assets.add(old_asset)
    version.assets.add(existing_asset)

    assign_perm('owner', user, version.dandiset)
    api_client.force_authenticate(user=user)

    resp = api_client.put(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{old_asset.uuid}/',
        {'metadata': existing_asset.metadata.metadata, 'blob_id': existing_asset.blob.blob_id},
        format='json',
    ).data

    # Updating an Asset to be the same as an existing Asset should still mint a new Asset
    assert resp['uuid'] != existing_asset.uuid


@pytest.mark.django_db
def test_asset_rest_update_unauthorized(api_client, version, asset):
    version.assets.add(asset)
    new_metadata = asset.metadata.metadata
    new_metadata['new_field'] = 'new_value'
    assert (
        api_client.put(
            f'/api/dandisets/{version.dandiset.identifier}/'
            f'versions/{version.version}/assets/{asset.uuid}/',
            {'metadata': new_metadata},
            format='json',
        ).status_code
        == 401
    )


@pytest.mark.django_db
def test_asset_rest_update_not_an_owner(api_client, user, version, asset):
    api_client.force_authenticate(user=user)
    version.assets.add(asset)

    new_metadata = asset.metadata.metadata
    new_metadata['new_field'] = 'new_value'
    assert (
        api_client.put(
            f'/api/dandisets/{version.dandiset.identifier}/'
            f'versions/{version.version}/assets/{asset.uuid}/',
            {'metadata': new_metadata},
            format='json',
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_asset_rest_delete(api_client, user, version, asset):
    api_client.force_authenticate(user=user)
    assign_perm('owner', user, version.dandiset)
    version.assets.add(asset)

    response = api_client.delete(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.uuid}/'
    )
    assert response.status_code == 204

    assert asset not in version.assets.all()
    assert asset in Asset.objects.all()


@pytest.mark.django_db
def test_asset_rest_delete_not_an_owner(api_client, user, version, asset):
    api_client.force_authenticate(user=user)
    version.assets.add(asset)

    response = api_client.delete(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/{asset.uuid}/'
    )
    assert response.status_code == 403

    assert asset in Asset.objects.all()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'path_prefix,results',
    [
        ('', ['foo/', 'no-root.nwb', 'root.nwb']),
        ('/', ['foo/', 'root.nwb']),
        ('/foo', ['bar/', 'baz.nwb']),
        ('/foo/', ['bar/', 'baz.nwb']),
    ],
)
def test_asset_rest_path_filter(api_client, version, asset_factory, path_prefix, results):
    paths = ['/foo/bar/file.nwb', '/foo/baz.nwb', '/root.nwb', 'no-root.nwb']
    for path in paths:
        version.assets.add(asset_factory(path=path))
    partial_path_assets = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/paths/',
        {'path_prefix': path_prefix},
    ).data

    assert partial_path_assets == results
