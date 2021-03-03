from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api.models import Asset

from .fuzzy import TIMESTAMP_RE, UUID_RE

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
def test_asset_rest_list(api_client, asset):
    assert api_client.get(
        f'/api/dandisets/{asset.version.dandiset.identifier}/'
        f'versions/{asset.version.version}/assets/'
    ).data == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'uuid': str(asset.uuid),
                'path': asset.path,
                'size': asset.size,
                'sha256': asset.sha256,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                # 'metadata': asset.metadata,
                'version': {
                    'dandiset': {
                        'identifier': asset.version.dandiset.identifier,
                        'created': TIMESTAMP_RE,
                        'modified': TIMESTAMP_RE,
                    },
                    'version': asset.version.version,
                    'name': asset.version.name,
                    'created': TIMESTAMP_RE,
                    'modified': TIMESTAMP_RE,
                    'asset_count': 1,
                    'size': asset.size,
                },
            }
        ],
    }


@pytest.mark.django_db
def test_asset_rest_retrieve(api_client, asset):
    assert api_client.get(
        f'/api/dandisets/{asset.version.dandiset.identifier}/'
        f'versions/{asset.version.version}/assets/{asset.uuid}/'
    ).data == {
        **asset.metadata.metadata,
        'identifier': str(asset.uuid),
        'contentUrl': [
            f'https://api.dandiarchive.org/api/dandisets/{asset.version.dandiset.identifier}'
            f'/versions/{asset.version.version}/assets/{asset.uuid}/download/',
            asset.blob.blob.url,
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
        {'metadata': metadata, 'sha256': asset_blob.sha256},
        format='json',
    ).data == {
        'uuid': UUID_RE,
        'path': path,
        'sha256': asset_blob.sha256,
        'size': asset_blob.size,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'version': {
            'dandiset': {
                'identifier': version.dandiset.identifier,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
            },
            'version': version.version,
            'name': version.name,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
            'asset_count': 1,
            'size': asset_blob.size,
        },
        'metadata': metadata,
    }

    asset = Asset.objects.get(blob__sha256=asset_blob.sha256, version=version)
    assert asset.metadata.metadata == metadata


@pytest.mark.django_db
def test_asset_create_no_valid_blob(api_client, user, version):
    assign_perm('owner', user, version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/no/valid/blob.txt'
    metadata = {'meta': 'data', 'foo': ['bar', 'baz'], '1': 2}
    sha256 = 'f' * 64

    assert (
        api_client.post(
            f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
            {'path': path, 'metadata': metadata, 'sha256': sha256},
            format='json',
        ).data
        == {'detail': 'Not found.'}
    )


@pytest.mark.django_db
def test_asset_create_no_path(api_client, user, version):
    assign_perm('owner', user, version.dandiset)
    api_client.force_authenticate(user=user)

    path = 'test/create/no/valid/blob.txt'
    metadata = {'meta': 'data', 'foo': ['bar', 'baz'], '1': 2}
    sha256 = 'f' * 64

    assert (
        api_client.post(
            f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
            {'path': path, 'metadata': metadata, 'sha256': sha256},
            format='json',
        ).data
        == {'detail': 'Not found.'}
    )


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
def test_asset_create_duplicate(api_client, user, asset):
    version = asset.version
    assign_perm('owner', user, version.dandiset)
    api_client.force_authenticate(user=user)

    resp = api_client.post(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/',
        {
            'path': asset.path,
            'metadata': asset.metadata.metadata,
            'sha256': asset.sha256,
        },
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == 'Asset Already Exists'


@pytest.mark.django_db
def test_asset_rest_update(api_client, user, asset, asset_blob):
    assign_perm('owner', user, asset.version.dandiset)
    api_client.force_authenticate(user=user)

    new_path = 'test/asset/rest/update.txt'
    new_metadata = {'path': new_path, 'foo': 'bar', 'num': 123, 'list': ['a', 'b', 'c']}
    new_sha256 = asset_blob.sha256

    assert api_client.put(
        f'/api/dandisets/{asset.version.dandiset.identifier}/'
        f'versions/{asset.version.version}/assets/{asset.uuid}/',
        {'metadata': new_metadata, 'sha256': new_sha256},
        format='json',
    ).data == {
        'uuid': str(asset.uuid),
        'path': new_path,
        'size': asset_blob.size,
        'sha256': new_sha256,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'version': {
            'dandiset': {
                'identifier': asset.version.dandiset.identifier,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
            },
            'version': asset.version.version,
            'name': asset.version.name,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
            'asset_count': 1,
            'size': asset_blob.size,
        },
        'metadata': new_metadata,
    }

    asset.refresh_from_db()
    assert asset.metadata.metadata == new_metadata


@pytest.mark.django_db
def test_asset_rest_update_unauthorized(api_client, asset):
    new_metadata = asset.metadata.metadata
    new_metadata['new_field'] = 'new_value'
    assert (
        api_client.put(
            f'/api/dandisets/{asset.version.dandiset.identifier}/'
            f'versions/{asset.version.version}/assets/{asset.uuid}/',
            {'metadata': new_metadata},
            format='json',
        ).status_code
        == 401
    )


@pytest.mark.django_db
def test_asset_rest_update_not_an_owner(api_client, user, asset):
    api_client.force_authenticate(user=user)

    new_metadata = asset.metadata.metadata
    new_metadata['new_field'] = 'new_value'
    assert (
        api_client.put(
            f'/api/dandisets/{asset.version.dandiset.identifier}/'
            f'versions/{asset.version.version}/assets/{asset.uuid}/',
            {'metadata': new_metadata},
            format='json',
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_asset_rest_delete(api_client, user, asset):
    api_client.force_authenticate(user=user)
    assign_perm('owner', user, asset.version.dandiset)

    response = api_client.delete(
        f'/api/dandisets/{asset.version.dandiset.identifier}/'
        f'versions/{asset.version.version}/assets/{asset.uuid}/'
    )
    assert response.status_code == 204

    assert not Asset.objects.all()


@pytest.mark.django_db
def test_asset_rest_delete_not_an_owner(api_client, user, asset):
    api_client.force_authenticate(user=user)

    response = api_client.delete(
        f'/api/dandisets/{asset.version.dandiset.identifier}/'
        f'versions/{asset.version.version}/assets/{asset.uuid}/'
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
    asset_factory(version=version, path='/foo/bar/file.nwb')
    asset_factory(version=version, path='/foo/baz.nwb')
    asset_factory(version=version, path='/root.nwb')
    asset_factory(version=version, path='no-root.nwb')
    partial_path_assets = api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/paths/',
        {'path_prefix': path_prefix},
    ).data

    assert partial_path_assets == results
