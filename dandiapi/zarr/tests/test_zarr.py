from __future__ import annotations

import pytest
from zarr_checksum.checksum import EMPTY_CHECKSUM

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.services.permissions.dandiset import (
    add_dandiset_owner,
    get_dandiset_owners,
    replace_dandiset_owners,
)
from dandiapi.api.tests.factories import DandisetFactory
from dandiapi.api.tests.fuzzy import UUID_RE
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus
from dandiapi.zarr.tasks import ingest_zarr_archive


@pytest.mark.django_db
def test_zarr_rest_create(authenticated_api_client, user):
    dandiset = DandisetFactory.create(owners=[user])
    name = 'My Zarr File!'

    resp = authenticated_api_client.post(
        '/api/zarr/',
        {
            'name': name,
            'dandiset': dandiset.identifier,
        },
    )
    assert resp.json() == {
        'name': name,
        'zarr_id': UUID_RE,
        'dandiset': dandiset.identifier,
        'status': ZarrArchiveStatus.PENDING,
        'checksum': None,
        'file_count': 0,
        'size': 0,
    }
    assert resp.status_code == 200

    zarr_archive = ZarrArchive.objects.get(zarr_id=resp.json()['zarr_id'])
    assert zarr_archive.name == name


@pytest.mark.django_db
def test_zarr_rest_dandiset_malformed(authenticated_api_client, user):
    dandiset = DandisetFactory.create(owners=[user])
    resp = authenticated_api_client.post(
        '/api/zarr/',
        {
            'name': 'My Zarr File!',
            'dandiset': f'{dandiset.identifier}asd',
        },
    )
    assert resp.status_code == 400
    assert resp.json() == {'dandiset': ['This value does not match the required pattern.']}


@pytest.mark.django_db
def test_zarr_rest_create_not_an_owner(authenticated_api_client, zarr_archive):
    resp = authenticated_api_client.post(
        '/api/zarr/',
        {
            'name': zarr_archive.name,
            'dandiset': zarr_archive.dandiset.identifier,
        },
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_zarr_rest_create_duplicate(authenticated_api_client, user, zarr_archive):
    add_dandiset_owner(zarr_archive.dandiset, user)
    resp = authenticated_api_client.post(
        '/api/zarr/',
        {
            'name': zarr_archive.name,
            'dandiset': zarr_archive.dandiset.identifier,
        },
    )
    assert resp.status_code == 400
    assert resp.json() == ['Zarr already exists']


@pytest.mark.django_db
def test_zarr_rest_create_embargoed_dandiset(
    authenticated_api_client,
    user,
    zarr_archive,
):
    dandiset = DandisetFactory.create(
        embargo_status=Dandiset.EmbargoStatus.EMBARGOED, owners=[user]
    )
    resp = authenticated_api_client.post(
        '/api/zarr/',
        {
            'name': zarr_archive.name,
            'dandiset': dandiset.identifier,
        },
    )
    assert resp.status_code == 200

    # Ensure this zarr is embargoed
    zarr = ZarrArchive.objects.get(zarr_id=resp.json()['zarr_id'])
    assert zarr.embargoed


@pytest.mark.django_db
def test_zarr_rest_create_unembargoing(authenticated_api_client, user, zarr_archive):
    dandiset = DandisetFactory.create(
        embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING, owners=[user]
    )
    resp = authenticated_api_client.post(
        '/api/zarr/',
        {
            'name': zarr_archive.name,
            'dandiset': dandiset.identifier,
        },
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_zarr_rest_get(authenticated_api_client, zarr_archive_factory, zarr_file_factory):
    zarr_archive = zarr_archive_factory(status=ZarrArchiveStatus.UPLOADED)
    zarr_file = zarr_file_factory(zarr_archive=zarr_archive)

    # Ingest
    ingest_zarr_archive(zarr_archive.zarr_id)
    zarr_archive.refresh_from_db()

    resp = authenticated_api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/')
    assert resp.status_code == 200
    assert resp.json() == {
        'name': zarr_archive.name,
        'zarr_id': str(zarr_archive.zarr_id),
        'dandiset': zarr_archive.dandiset.identifier,
        'status': ZarrArchiveStatus.COMPLETE,
        'checksum': zarr_archive.checksum,
        'file_count': 1,
        'size': zarr_file.size,
    }


@pytest.mark.django_db
def test_zarr_rest_get_embargoed(authenticated_api_client, user, embargoed_zarr_archive_factory):
    dandiset = DandisetFactory.create(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    embargoed_zarr_archive = embargoed_zarr_archive_factory(dandiset=dandiset)
    assert user not in get_dandiset_owners(embargoed_zarr_archive.dandiset)

    resp = authenticated_api_client.get(f'/api/zarr/{embargoed_zarr_archive.zarr_id}/')
    assert resp.status_code == 404

    replace_dandiset_owners(embargoed_zarr_archive.dandiset, [user])
    resp = authenticated_api_client.get(f'/api/zarr/{embargoed_zarr_archive.zarr_id}/')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_zarr_rest_list_embargoed(authenticated_api_client, user, zarr_archive_factory):
    open_dandiset = DandisetFactory.create(embargo_status=Dandiset.EmbargoStatus.OPEN)
    embargoed_dandiset = DandisetFactory.create(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)

    # Create some embargoed and some open zarrs
    open_zarrs = [zarr_archive_factory(dandiset=open_dandiset) for _ in range(3)]
    embargoed_zarrs = [zarr_archive_factory(dandiset=embargoed_dandiset) for _ in range(3)]

    # Assert only open zarrs are returned
    zarrs = authenticated_api_client.get('/api/zarr/').json()['results']
    assert sorted(z['zarr_id'] for z in zarrs) == sorted(z.zarr_id for z in open_zarrs)

    # Assert that all zarrs returned when user has access to embargoed zarrs
    replace_dandiset_owners(embargoed_dandiset, [user])
    zarrs = authenticated_api_client.get('/api/zarr/').json()['results']
    assert len(zarrs) == len(open_zarrs + embargoed_zarrs)
    assert sorted(z['zarr_id'] for z in zarrs) == sorted(
        z.zarr_id for z in (open_zarrs + embargoed_zarrs)
    )


@pytest.mark.django_db
def test_zarr_rest_list_filter(authenticated_api_client, zarr_archive_factory):
    # Create dandisets and zarrs
    dandiset_a: Dandiset = DandisetFactory.create()
    zarr_archive_a_a: ZarrArchive = zarr_archive_factory(dandiset=dandiset_a, name='test')
    zarr_archive_a_b: ZarrArchive = zarr_archive_factory(dandiset=dandiset_a, name='unique')

    dandiset_b: Dandiset = DandisetFactory.create()
    zarr_archive_b_a: ZarrArchive = zarr_archive_factory(dandiset=dandiset_b, name='test')
    zarr_archive_b_b: ZarrArchive = zarr_archive_factory(dandiset=dandiset_b, name='unique2')

    # Test dandiset filter with dandiset a
    resp = authenticated_api_client.get('/api/zarr/', {'dandiset': dandiset_a.identifier})
    assert resp.status_code == 200
    results = resp.json()['results']
    assert len(results) == 2
    assert results[0]['zarr_id'] == zarr_archive_a_a.zarr_id
    assert results[1]['zarr_id'] == zarr_archive_a_b.zarr_id

    # Test dandiset filter with dandiset b
    resp = authenticated_api_client.get('/api/zarr/', {'dandiset': dandiset_b.identifier})
    assert resp.status_code == 200
    results = resp.json()['results']
    assert len(results) == 2
    assert results[0]['zarr_id'] == zarr_archive_b_a.zarr_id
    assert results[1]['zarr_id'] == zarr_archive_b_b.zarr_id

    # Test name filter
    resp = authenticated_api_client.get('/api/zarr/', {'name': 'test'})
    assert resp.status_code == 200
    results = resp.json()['results']
    assert len(results) == 2
    assert results[0]['zarr_id'] == zarr_archive_a_a.zarr_id
    assert results[1]['zarr_id'] == zarr_archive_b_a.zarr_id

    # Test dandiset and name filter
    resp = authenticated_api_client.get('/api/zarr/', {'dandiset': dandiset_b, 'name': 'test'})
    assert resp.status_code == 200
    results = resp.json()['results']
    assert len(results) == 1
    assert results[0]['zarr_id'] == zarr_archive_b_a.zarr_id


@pytest.mark.django_db
def test_zarr_rest_get_very_big(authenticated_api_client, zarr_archive_factory):
    ten_quadrillion = 10**16
    ten_petabytes = 10**16
    zarr_archive = zarr_archive_factory(file_count=ten_quadrillion, size=ten_petabytes)
    assert zarr_archive.file_count == ten_quadrillion
    assert zarr_archive.size == ten_petabytes

    # Don't ingest since there aren't actually any files
    resp = authenticated_api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/')
    assert resp.status_code == 200
    assert resp.json() == {
        'name': zarr_archive.name,
        'zarr_id': zarr_archive.zarr_id,
        'dandiset': zarr_archive.dandiset.identifier,
        'status': ZarrArchiveStatus.PENDING,
        'checksum': zarr_archive.checksum,
        'file_count': ten_quadrillion,
        'size': ten_petabytes,
    }


@pytest.mark.django_db
def test_zarr_rest_get_empty(authenticated_api_client, zarr_archive: ZarrArchive):
    resp = authenticated_api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/')
    assert resp.status_code == 200
    assert resp.json() == {
        'name': zarr_archive.name,
        'zarr_id': zarr_archive.zarr_id,
        'dandiset': zarr_archive.dandiset.identifier,
        'status': ZarrArchiveStatus.PENDING,
        'checksum': zarr_archive.checksum,
        'file_count': 0,
        'size': 0,
    }


@pytest.mark.django_db
def test_zarr_rest_delete_file(
    authenticated_api_client,
    user,
    zarr_archive_factory,
    zarr_file_factory,
):
    # Create zarr and assign user perms
    zarr_archive = zarr_archive_factory(status=ZarrArchiveStatus.UPLOADED)
    add_dandiset_owner(zarr_archive.dandiset, user)

    # Upload file and ingest
    zarr_file = zarr_file_factory(zarr_archive=zarr_archive)
    ingest_zarr_archive(zarr_archive.zarr_id)

    # Assert file count and size
    zarr_archive.refresh_from_db()
    assert zarr_archive.file_count == 1
    assert zarr_archive.size == zarr_file.size

    # Make delete call
    resp = authenticated_api_client.delete(
        f'/api/zarr/{zarr_archive.zarr_id}/files/', [{'path': str(zarr_file.path)}]
    )
    assert resp.status_code == 204
    assert not zarr_archive.storage.exists(zarr_archive.s3_path(str(zarr_file.path)))

    # Assert zarr is back in pending state
    zarr_archive.refresh_from_db()
    assert zarr_archive.status == ZarrArchiveStatus.PENDING
    assert zarr_archive.checksum is None
    assert zarr_archive.file_count == 0
    assert zarr_archive.size == 0

    # Re-ingest
    zarr_archive.status = ZarrArchiveStatus.UPLOADED
    zarr_archive.save()
    ingest_zarr_archive(zarr_archive.zarr_id)

    zarr_archive.refresh_from_db()
    assert zarr_archive.checksum == EMPTY_CHECKSUM
    assert zarr_archive.file_count == 0
    assert zarr_archive.size == 0


@pytest.mark.django_db
def test_zarr_rest_delete_file_asset_metadata(
    authenticated_api_client,
    user,
    zarr_archive_factory,
    zarr_file_factory,
    asset_factory,
):
    zarr_archive = zarr_archive_factory(status=ZarrArchiveStatus.UPLOADED)
    add_dandiset_owner(zarr_archive.dandiset, user)

    asset = asset_factory(zarr=zarr_archive, blob=None)

    zarr_file = zarr_file_factory(zarr_archive=zarr_archive)
    ingest_zarr_archive(zarr_archive.zarr_id)

    asset.refresh_from_db()
    zarr_archive.refresh_from_db()
    assert asset.full_metadata['digest'] == zarr_archive.digest
    assert asset.full_metadata['contentSize'] == 100

    resp = authenticated_api_client.delete(
        f'/api/zarr/{zarr_archive.zarr_id}/files/', [{'path': str(zarr_file.path)}]
    )
    assert resp.status_code == 204

    # Re-ingest
    zarr_archive.refresh_from_db()
    zarr_archive.status = ZarrArchiveStatus.UPLOADED
    zarr_archive.save()
    ingest_zarr_archive(zarr_archive.zarr_id)

    # Assert now empty
    asset.refresh_from_db()
    assert asset.full_metadata['digest']['dandi:dandi-zarr-checksum'] == EMPTY_CHECKSUM
    assert asset.full_metadata['contentSize'] == 0


@pytest.mark.django_db
def test_zarr_rest_delete_file_not_an_owner(
    authenticated_api_client, zarr_archive: ZarrArchive, zarr_file_factory
):
    zarr_file = zarr_file_factory(zarr_archive=zarr_archive)

    resp = authenticated_api_client.delete(
        f'/api/zarr/{zarr_archive.zarr_id}/files/', [{'path': str(zarr_file.path)}]
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_zarr_rest_delete_multiple_files(
    authenticated_api_client,
    user,
    zarr_archive: ZarrArchive,
    zarr_file_factory,
):
    add_dandiset_owner(zarr_archive.dandiset, user)

    # Create 10 files
    zarr_files = [zarr_file_factory(zarr_archive=zarr_archive) for _ in range(10)]

    resp = authenticated_api_client.delete(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        [{'path': str(file.path)} for file in zarr_files],
    )
    assert resp.status_code == 204

    # Assert not found
    for file in zarr_files:
        assert not zarr_archive.storage.exists(zarr_archive.s3_path(str(file.path)))

    ingest_zarr_archive(zarr_archive.zarr_id)
    zarr_archive.refresh_from_db()
    assert zarr_archive.file_count == 0
    assert zarr_archive.size == 0


@pytest.mark.django_db
def test_zarr_rest_delete_missing_file(
    authenticated_api_client,
    user,
    zarr_archive: ZarrArchive,
    zarr_file_factory,
):
    add_dandiset_owner(zarr_archive.dandiset, user)

    zarr_file = zarr_file_factory(zarr_archive=zarr_archive)
    resp = authenticated_api_client.delete(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        [
            {'path': str(zarr_file.path)},
            {'path': 'does/not/exist'},
        ],
    )
    assert resp.status_code == 400
    assert resp.json() == [f'File test-zarr/{zarr_archive.zarr_id}/does/not/exist does not exist.']
    assert zarr_archive.storage.exists(zarr_archive.s3_path(str(zarr_file.path)))

    # Ingest
    zarr_archive.status = ZarrArchiveStatus.UPLOADED
    zarr_archive.save()
    ingest_zarr_archive(zarr_archive.zarr_id)

    # Check
    zarr_archive.refresh_from_db()
    assert zarr_archive.file_count == 1
    assert zarr_archive.size == zarr_file.size


@pytest.mark.django_db
def test_zarr_file_list(api_client, zarr_archive: ZarrArchive, zarr_file_factory):
    files = [
        'foo/bar/a.txt',
        'foo/bar/b.txt',
        'foo/baz.txt',
        # These two files are here just to demonstrate filtering
        'bar/a.txt',
        'bar/b.txt',
    ]
    for file in files:
        zarr_file_factory(zarr_archive=zarr_archive, path=file)

    # Check base listing
    resp = api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/files/')
    assert [x['Key'] for x in resp.json()['results']] == sorted(files)

    # Check that prefix query param works as expected
    resp = api_client.get(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        {'prefix': 'foo/'},
    )
    assert [x['Key'] for x in resp.json()['results']] == [
        'foo/bar/a.txt',
        'foo/bar/b.txt',
        'foo/baz.txt',
    ]

    # Check that prefix and after work together
    resp = api_client.get(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        {'prefix': 'foo/', 'after': 'foo/bar/a.txt'},
    )
    assert [x['Key'] for x in resp.json()['results']] == ['foo/bar/b.txt', 'foo/baz.txt']

    # Use limit query param
    resp = api_client.get(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        {'prefix': 'foo/', 'after': 'foo/bar/a.txt', 'limit': 1},
    )
    assert [x['Key'] for x in resp.json()['results']] == ['foo/bar/b.txt']

    # Check download flag
    resp = api_client.get(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        {'prefix': 'foo/bar/a.txt', 'download': True},
    )
    assert resp.status_code == 302
    assert f'/test-zarr/{zarr_archive.zarr_id}/foo/bar/a.txt?' in resp.headers['Location']


@pytest.mark.django_db
def test_zarr_explore_head(api_client, zarr_archive: ZarrArchive):
    filepath = 'foo/bar.txt'
    resp = api_client.head(f'/api/zarr/{zarr_archive.zarr_id}/files/', {'prefix': filepath})
    assert resp.status_code == 302
    assert f'/test-zarr/{zarr_archive.zarr_id}/{filepath}?' in resp.headers['Location']
