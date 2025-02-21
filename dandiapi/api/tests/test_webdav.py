from __future__ import annotations

from django.conf import settings
import pytest

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.services.asset import add_asset_to_version
from dandiapi.api.services.permissions.dandiset import add_dandiset_owner


@pytest.mark.django_db
def test_asset_atpath_root_path(api_client, user, draft_version, asset_blob):
    add_dandiset_owner(dandiset=draft_version.dandiset, user=user)
    add_asset_to_version(
        user=user,
        version=draft_version,
        asset_blob=asset_blob,
        metadata={
            'path': 'a.txt',
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        },
    )
    add_asset_to_version(
        user=user,
        version=draft_version,
        asset_blob=asset_blob,
        metadata={
            'path': 'b.txt',
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        },
    )

    # Test that children=False produces an empty list at the root
    api_client.force_authenticate(user=user)
    resp = api_client.get(
        '/api/webdav/assets/atpath',
        {
            'children': False,
            'dandiset_id': draft_version.dandiset.identifier,
            'version_id': draft_version.version,
        },
    )
    assert resp.status_code == 200
    assert resp.json()['count'] == 0
    assert len(resp.json()['results']) == 0

    # Test that children=True produces the assets that we know exist
    resp = api_client.get(
        '/api/webdav/assets/atpath',
        {
            'children': True,
            'dandiset_id': draft_version.dandiset.identifier,
            'version_id': draft_version.version,
        },
    )
    assert resp.status_code == 200
    assert resp.json()['count'] == 2
    assert resp.json()['results'][0]['type'] == 'asset'
    assert resp.json()['results'][0]['resource']['path'] == 'a.txt'
    assert resp.json()['results'][1]['type'] == 'asset'
    assert resp.json()['results'][1]['resource']['path'] == 'b.txt'


@pytest.mark.django_db
def test_asset_atpath_asset(api_client, user, draft_version, asset_blob):
    add_dandiset_owner(dandiset=draft_version.dandiset, user=user)
    path = 'foo.txt'
    asset = add_asset_to_version(
        user=user,
        version=draft_version,
        asset_blob=asset_blob,
        metadata={
            'path': path,
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        },
    )

    # Path points directly to asset
    api_client.force_authenticate(user=user)
    resp = api_client.get(
        '/api/webdav/assets/atpath',
        {
            'children': False,
            'dandiset_id': draft_version.dandiset.identifier,
            'version_id': draft_version.version,
            'path': path,
        },
    )
    assert resp.status_code == 200
    assert resp.json()['count'] == 1

    res = resp.json()['results'][0]
    assert res['type'] == 'asset'
    assert res['resource']['asset_id'] == str(asset.asset_id)
    assert 'metadata' not in res['resource']

    # The children param should have no effect
    second_resp = api_client.get(
        '/api/webdav/assets/atpath',
        {
            'children': True,
            'dandiset_id': draft_version.dandiset.identifier,
            'version_id': draft_version.version,
            'path': path,
        },
    )
    assert resp.json() == second_resp.json()

    # metadata=True should add the metadata field
    resp = api_client.get(
        '/api/webdav/assets/atpath',
        {
            'metadata': True,
            'dandiset_id': draft_version.dandiset.identifier,
            'version_id': draft_version.version,
            'path': path,
        },
    )
    assert 'metadata' in resp.json()['results'][0]['resource']


@pytest.mark.django_db
def test_asset_atpath_folder(api_client, user, draft_version, asset_blob):
    # Create the following directory structure
    # foo/
    #   bar.txt
    #   baz.txt
    add_dandiset_owner(dandiset=draft_version.dandiset, user=user)
    add_asset_to_version(
        user=user,
        version=draft_version,
        asset_blob=asset_blob,
        metadata={
            'path': 'foo/bar.txt',
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        },
    )
    add_asset_to_version(
        user=user,
        version=draft_version,
        asset_blob=asset_blob,
        metadata={
            'path': 'foo/baz.txt',
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        },
    )

    # Assert that only the folder itself is returned if children=False
    api_client.force_authenticate(user=user)
    resp = api_client.get(
        '/api/webdav/assets/atpath',
        {
            'children': False,
            'dandiset_id': draft_version.dandiset.identifier,
            'version_id': draft_version.version,
            'path': 'foo',
        },
    )
    assert resp.status_code == 200
    assert resp.json()['count'] == 1
    assert resp.json()['results'][0]['type'] == 'folder'
    assert resp.json()['results'][0]['resource']['path'] == 'foo'

    # Now test that children=True includes the assets
    resp = api_client.get(
        '/api/webdav/assets/atpath',
        {
            'children': True,
            'dandiset_id': draft_version.dandiset.identifier,
            'version_id': draft_version.version,
            'path': 'foo',
        },
    )
    assert resp.status_code == 200
    assert resp.json()['count'] == 3
    assert resp.json()['results'][0]['type'] == 'folder'
    assert resp.json()['results'][1]['type'] == 'asset'
    assert resp.json()['results'][2]['type'] == 'asset'


@pytest.mark.django_db
def test_asset_atpath_path_missing(api_client, user, draft_version, asset_blob):
    add_dandiset_owner(dandiset=draft_version.dandiset, user=user)
    add_asset_to_version(
        user=user,
        version=draft_version,
        asset_blob=asset_blob,
        metadata={
            'path': 'foo/bar.txt',
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        },
    )

    api_client.force_authenticate(user=user)
    resp = api_client.get(
        '/api/webdav/assets/atpath',
        {
            'children': False,
            'dandiset_id': draft_version.dandiset.identifier,
            'version_id': draft_version.version,
            'path': 'foobartxt',
        },
    )
    assert resp.status_code == 200
    assert resp.json()['count'] == 0


@pytest.mark.django_db
def test_asset_atpath_path_incorrect_dandiset_id(api_client, user, draft_version, asset_blob):
    api_client.force_authenticate(user=user)
    resp = api_client.get(
        '/api/webdav/assets/atpath',
        {
            'children': False,
            'dandiset_id': '123456',
            'version_id': 'draft',
            'path': '',
        },
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_asset_atpath_path_incorrect_version_id(api_client, user, draft_version, asset_blob):
    api_client.force_authenticate(user=user)
    resp = api_client.get(
        '/api/webdav/assets/atpath',
        {
            'children': False,
            'dandiset_id': draft_version.dandiset,
            'version_id': 'typo',
            'path': '',
        },
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_asset_atpath_embargoed_access(
    api_client, user_factory, dandiset_factory, draft_version_factory
):
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    draft_version = draft_version_factory(dandiset=dandiset)

    user = user_factory()
    api_client.force_authenticate(user=user)
    resp = api_client.get(
        '/api/webdav/assets/atpath',
        {
            'children': False,
            'dandiset_id': draft_version.dandiset.identifier,
            'version_id': draft_version.version,
            'path': '',
        },
    )
    assert resp.status_code == 403

    add_dandiset_owner(dandiset, user)
    resp = api_client.get(
        '/api/webdav/assets/atpath',
        {
            'children': False,
            'dandiset_id': draft_version.dandiset.identifier,
            'version_id': draft_version.version,
            'path': '',
        },
    )
    assert resp.status_code == 200
