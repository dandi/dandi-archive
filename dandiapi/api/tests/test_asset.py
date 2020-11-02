from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api.models import Asset

from .fuzzy import TIMESTAMP_RE

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
                'uuid': asset.uuid,
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
        f'versions/{asset.version.version}/assets/{asset.path}/'
    ).data == {
        'uuid': asset.uuid,
        'path': asset.path,
        'size': asset.size,
        'sha256': asset.sha256,
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
            'size': asset.size,
        },
        'metadata': asset.metadata.metadata,
    }


@pytest.mark.django_db
def test_asset_rest_update(api_client, user, asset):
    assign_perm('owner', user, asset.version.dandiset)
    api_client.force_authenticate(user=user)

    new_metadata = asset.metadata.metadata
    new_metadata['new_field'] = 'new_value'
    assert api_client.put(
        f'/api/dandisets/{asset.version.dandiset.identifier}/'
        f'versions/{asset.version.version}/assets/{asset.path}/',
        {'metadata': new_metadata},
        format='json',
    ).data == {
        'uuid': asset.uuid,
        'path': asset.path,
        'size': asset.size,
        'sha256': asset.sha256,
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
            'size': asset.size,
        },
        'metadata': new_metadata,
    }


@pytest.mark.django_db
def test_asset_rest_update_unauthorized(api_client, asset):
    new_metadata = asset.metadata.metadata
    new_metadata['new_field'] = 'new_value'
    assert (
        api_client.put(
            f'/api/dandisets/{asset.version.dandiset.identifier}/'
            f'versions/{asset.version.version}/assets/{asset.path}/',
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
            f'versions/{asset.version.version}/assets/{asset.path}/',
            {'metadata': new_metadata},
            format='json',
        ).status_code
        == 403
    )


# @pytest.mark.django_db
# @pytest.mark.parametrize(
#     'new_path,expected',
#     [
#         # Partial
#         (lambda path: path[: int(len(path) / 2)], True),
#         # Full
#         (lambda path: path, True),
#         # Extra at beginning
#         (lambda path: 'extra-string' + path, False),
#         # Extra at end
#         (lambda path: path + 'extra-string', False),
#         # Case insensitive 1
#         (lambda path: path.upper(), True),
#         # Case insensitive 2
#         (lambda path: path.lower(), True),
#     ],
# )
# def test_asset_rest_path_filter(api_client, asset, new_path, expected):
#     path = new_path(asset.path)
#     partial_path_assets = api_client.get(
#         f'/api/dandisets/{asset.version.dandiset.identifier}/'
#         f'versions/{asset.version.version}/assets/paths/',
#         {'path': path},
#     ).data['results']

#     matching_results = [res for res in partial_path_assets if res['uuid'] == str(asset.uuid)]
#     assert bool(matching_results) is expected
