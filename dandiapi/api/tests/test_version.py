from __future__ import annotations

import datetime
from time import sleep
from typing import TYPE_CHECKING

from dandischema.models import AccessType
from django.conf import settings
from freezegun import freeze_time
import pytest

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.services.metadata import version_aggregate_assets_summary
from dandiapi.api.services.metadata.exceptions import VersionMetadataConcurrentlyModifiedError
from dandiapi.api.services.permissions.dandiset import add_dandiset_owner

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from rest_framework.test import APIClient

from dandiapi.api import tasks
from dandiapi.api.asset_paths import add_version_asset_paths
from dandiapi.api.models import Asset, Version
from dandiapi.api.services.publish import _build_publishable_version_from_draft
from dandiapi.zarr.tasks import ingest_zarr_archive

from .fuzzy import TIMESTAMP_RE, URN_RE, UTC_ISO_TIMESTAMP_RE, VERSION_ID_RE


@pytest.mark.django_db
def test_version_next_published_version_nosave(dandiset):
    # Without saving, the output should be reproducible
    version_str_1 = Version.next_published_version(dandiset)
    version_str_2 = Version.next_published_version(dandiset)
    assert version_str_1 == version_str_2
    assert version_str_1 == VERSION_ID_RE


@pytest.mark.django_db
def test_version_next_published_version_save(mocker, dandiset, published_version_factory):
    # Given an existing version at the current time, a different one should be allocated
    next_published_version_spy = mocker.spy(Version, 'next_published_version')
    version_1 = published_version_factory(dandiset=dandiset)
    next_published_version_spy.assert_called_once()

    version_str_2 = Version.next_published_version(dandiset)
    assert version_1.version != version_str_2


@pytest.mark.django_db
def test_version_next_published_version_simultaneous_save(
    dandiset_factory,
    published_version_factory,
):
    dandiset_1 = dandiset_factory()
    dandiset_2 = dandiset_factory()
    with freeze_time():
        # version strings have a time component. mock all functions that retrieve the
        # current time so the test isn't flaky at time boundaries.
        version_1 = published_version_factory(dandiset=dandiset_1)
        version_2 = published_version_factory(dandiset=dandiset_2)
    # Different dandisets published at the same time should have the same version string
    assert version_1.version == version_2.version


@pytest.mark.django_db
def test_draft_version_metadata_computed(draft_version: Version):
    original_metadata = {'schemaVersion': settings.DANDI_SCHEMA_VERSION}
    draft_version.metadata = original_metadata

    # Save the version to add computed properties to the metadata
    draft_version.save()

    expected_metadata = {
        **original_metadata,
        'manifestLocation': [
            f'{settings.DANDI_API_URL}/api/dandisets/{draft_version.dandiset.identifier}/versions/draft/assets/'
        ],
        'name': draft_version.name,
        'identifier': f'DANDI:{draft_version.dandiset.identifier}',
        'version': draft_version.version,
        'id': f'DANDI:{draft_version.dandiset.identifier}/{draft_version.version}',
        'url': (
            f'{settings.DANDI_WEB_APP_URL}/dandiset/'
            f'{draft_version.dandiset.identifier}/{draft_version.version}'
        ),
        'repository': settings.DANDI_WEB_APP_URL,
        'dateCreated': draft_version.dandiset.created.isoformat(),
        'access': [{'schemaKey': 'AccessRequirements', 'status': AccessType.OpenAccess.value}],
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',
        'assetsSummary': {
            'numberOfBytes': 0,
            'numberOfFiles': 0,
            'schemaKey': 'AssetsSummary',
        },
    }
    expected_metadata['citation'] = draft_version.citation(expected_metadata)

    assert draft_version.metadata == expected_metadata


@pytest.mark.django_db
def test_published_version_metadata_computed(published_version: Version):
    original_metadata = {'schemaVersion': settings.DANDI_SCHEMA_VERSION}
    published_version.metadata = original_metadata

    # Save the version to add computed properties to the metadata
    published_version.save()

    expected_metadata = {
        **original_metadata,
        'manifestLocation': [
            (
                f'http://{settings.MINIO_STORAGE_ENDPOINT}/test-dandiapi-dandisets'
                f'/test-prefix/dandisets/{published_version.dandiset.identifier}'
                f'/{published_version.version}/assets.yaml'
            )
        ],
        'name': published_version.name,
        'identifier': f'DANDI:{published_version.dandiset.identifier}',
        'version': published_version.version,
        'id': f'DANDI:{published_version.dandiset.identifier}/{published_version.version}',
        'doi': (
            f'10.80507/dandi.'
            f'{published_version.dandiset.identifier}/{published_version.version}'
        ),
        'url': (
            f'{settings.DANDI_WEB_APP_URL}/dandiset/'
            f'{published_version.dandiset.identifier}/{published_version.version}'
        ),
        'repository': settings.DANDI_WEB_APP_URL,
        'dateCreated': published_version.dandiset.created.isoformat(),
        'access': [{'schemaKey': 'AccessRequirements', 'status': AccessType.OpenAccess.value}],
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',
        'assetsSummary': {
            'numberOfBytes': 0,
            'numberOfFiles': 0,
            'schemaKey': 'AssetsSummary',
        },
    }
    expected_metadata['citation'] = published_version.citation(expected_metadata)

    assert published_version.metadata == expected_metadata


@pytest.mark.django_db
def test_version_metadata_citation_draft(draft_version):
    name = draft_version.metadata['name'].rstrip('.')
    year = datetime.datetime.now(datetime.UTC).year
    url = (
        f'{settings.DANDI_WEB_APP_URL}/dandiset/'
        f'{draft_version.dandiset.identifier}/{draft_version.version}'
    )
    assert (
        draft_version.metadata['citation']
        == f'{name} ({year}). (Version {draft_version.version}) [Data set]. DANDI Archive. {url}'
    )


@pytest.mark.django_db
def test_version_metadata_citation_published(published_version):
    name = published_version.metadata['name'].rstrip('.')
    year = datetime.datetime.now(datetime.UTC).year
    url = f'https://doi.org/{published_version.doi}'
    assert published_version.metadata['citation'] == (
        f'{name} ({year}). (Version {published_version.version}) [Data set]. '
        f'DANDI Archive. {url}'
    )


@pytest.mark.django_db
def test_version_metadata_citation_no_contributors(version):
    version.metadata['contributor'] = []
    version.save()

    name = version.metadata['name'].rstrip('.')
    year = datetime.datetime.now(datetime.UTC).year
    assert version.metadata['citation'].startswith(
        f'{name} ({year}). (Version {version.version}) [Data set]. DANDI Archive. '
    )


@pytest.mark.django_db
def test_version_metadata_citation_contributor_not_in_citation(version):
    version.metadata['contributor'] = [
        {'name': 'Jane Doe'},
        {'name': 'John Doe', 'includeInCitation': False},
    ]
    version.save()

    name = version.metadata['name'].rstrip('.')
    year = datetime.datetime.now(datetime.UTC).year
    assert version.metadata['citation'].startswith(
        f'{name} ({year}). (Version {version.version}) [Data set]. DANDI Archive. '
    )


@pytest.mark.django_db
def test_version_metadata_citation_contributor(version):
    version.metadata['contributor'] = [{'name': 'Doe, Jane', 'includeInCitation': True}]
    version.save()

    name = version.metadata['name'].rstrip('.')
    year = datetime.datetime.now(datetime.UTC).year
    assert version.metadata['citation'].startswith(
        f'Doe, Jane ({year}) {name} (Version {version.version}) [Data set]. DANDI Archive. '
    )


@pytest.mark.django_db
def test_version_metadata_citation_multiple_contributors(version):
    version.metadata['contributor'] = [
        {'name': 'John Doe', 'includeInCitation': True},
        {'name': 'Jane Doe', 'includeInCitation': True},
    ]
    version.save()

    name = version.metadata['name'].rstrip('.')
    year = datetime.datetime.now(datetime.UTC).year
    assert version.metadata['citation'].startswith(
        f'John Doe; Jane Doe ({year}) {name} (Version {version.version}) [Data set]. '
        f'DANDI Archive. '
    )


@pytest.mark.django_db
def test_version_metadata_context(version):
    version.metadata['schemaVersion'] = '6.6.6'
    version.save()

    assert version.metadata['@context'] == (
        'https://raw.githubusercontent.com/dandi/schema/master/releases/6.6.6/context.json'
    )


@pytest.mark.django_db
def test_version_metadata_assets_summary_missing(version, asset):
    version.assets.add(asset)

    # Verify that an Asset with no aggregatable metadata doesn't break anything
    version.save()


@pytest.mark.django_db
def test_version_aggregate_assets_summary_valid_assets(draft_version, draft_asset_factory):
    valid_asset = draft_asset_factory(status=Asset.Status.VALID)
    invalid_asset = draft_asset_factory(status=Asset.Status.INVALID)
    draft_version.assets.add(valid_asset, invalid_asset)
    version_aggregate_assets_summary(draft_version)
    draft_version.refresh_from_db()
    assert draft_version.metadata['assetsSummary']['numberOfFiles'] == 1


@pytest.mark.django_db
def test_version_valid_with_valid_asset(version, asset):
    version.assets.add(asset)

    version.status = Version.Status.VALID
    version.save()
    asset.status = Asset.Status.VALID
    asset.save()

    assert version.publishable


@pytest.mark.django_db
@pytest.mark.parametrize(
    'status',
    [
        Version.Status.PENDING,
        Version.Status.VALIDATING,
        Version.Status.INVALID,
    ],
)
def test_version_invalid(version, status):
    version.status = status
    version.save()

    assert not version.publishable


@pytest.mark.django_db
@pytest.mark.parametrize(
    'status',
    [
        Asset.Status.PENDING,
        Asset.Status.VALIDATING,
        Asset.Status.INVALID,
    ],
)
def test_version_valid_with_invalid_asset(version, asset, status):
    version.assets.add(asset)

    version.status = Version.Status.VALID
    version.save()

    asset.status = status
    asset.save()

    assert not version.publishable


@pytest.mark.django_db
def test_version_publish_version(draft_version, asset):
    # Normally the publish endpoint would inject a doi, so we must do it manually
    fake_doi = 'doi'

    draft_version.assets.add(asset)
    draft_version.save()

    publish_version = _build_publishable_version_from_draft(draft_version)
    publish_version.doi = fake_doi
    publish_version.save()

    assert publish_version.dandiset == draft_version.dandiset
    assert publish_version.metadata == {
        **draft_version.metadata,
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
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'datePublished': UTC_ISO_TIMESTAMP_RE,
        'manifestLocation': [
            f'http://{settings.MINIO_STORAGE_ENDPOINT}/test-dandiapi-dandisets/test-prefix/dandisets/{publish_version.dandiset.identifier}/{publish_version.version}/assets.yaml',
        ],
        'identifier': f'DANDI:{publish_version.dandiset.identifier}',
        'version': publish_version.version,
        'id': f'DANDI:{publish_version.dandiset.identifier}/{publish_version.version}',
        'url': (
            f'{settings.DANDI_WEB_APP_URL}/dandiset/{publish_version.dandiset.identifier}'
            f'/{publish_version.version}'
        ),
        'citation': publish_version.citation(publish_version.metadata),
        'doi': fake_doi,
        # The published_version cannot have a properly defined assetsSummary yet, since that would
        # require having created rows the Asset-to-Version join table, which is a side affect.
        'assetsSummary': {
            'schemaKey': 'AssetsSummary',
            'numberOfBytes': 0,
            'numberOfFiles': 0,
        },
    }


@pytest.mark.django_db
def test_version_aggregate_assets_summary(draft_version_factory, draft_asset_factory):
    version = draft_version_factory(status=Version.Status.VALID)
    asset = draft_asset_factory(status=Asset.Status.VALID)
    version.assets.add(asset)

    version_aggregate_assets_summary(version)
    version.refresh_from_db()

    assert version.metadata['assetsSummary']['numberOfBytes'] == asset.blob.size
    assert version.metadata['assetsSummary']['numberOfFiles'] == 1
    assert version.metadata['assetsSummary']['schemaKey'] == 'AssetsSummary'


@pytest.mark.django_db
def test_version_publish_updates_draft_version_assets_summary(
    draft_version_factory, draft_asset_factory, user
):
    version = draft_version_factory(status=Version.Status.PUBLISHING)
    asset = draft_asset_factory(status=Asset.Status.VALID)
    version.assets.add(asset)

    tasks.publish_dandiset_task(version.dandiset.id, user.id)

    version.refresh_from_db()
    draft_asset_summary = version.metadata['assetsSummary']
    published_asset_summary = Version.objects.latest('created').metadata['assetsSummary']

    assert published_asset_summary == draft_asset_summary


@pytest.mark.django_db
def test_version_aggregate_assets_summary_metadata_modified(
    draft_version_factory, draft_asset_factory
):
    version = draft_version_factory(status=Version.Status.VALID)
    asset = draft_asset_factory(status=Asset.Status.VALID)
    version.assets.add(asset)

    # Modify the metadata passed to the function so that it's mismatched
    version.metadata['foo'] = 'bar'
    with pytest.raises(VersionMetadataConcurrentlyModifiedError):
        version_aggregate_assets_summary(version)


@pytest.mark.django_db
def test_version_size(
    version,
    asset_factory,
    asset_blob_factory,
    embargoed_asset_blob_factory,
    zarr_archive_factory,
):
    version.assets.add(asset_factory(blob=asset_blob_factory(size=100)))
    version.assets.add(asset_factory(blob=embargoed_asset_blob_factory(size=200)))
    version.assets.add(asset_factory(blob=None, zarr=zarr_archive_factory(size=400)))
    add_version_asset_paths(version=version)

    assert version.size == 700


@pytest.mark.django_db
def test_version_rest_list(api_client, version, draft_version_factory):
    # Create an extra version so that there are multiple versions to filter down
    draft_version_factory()

    assert api_client.get(f'/api/dandisets/{version.dandiset.identifier}/versions/').data == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'dandiset': {
                    'identifier': version.dandiset.identifier,
                    'created': TIMESTAMP_RE,
                    'modified': TIMESTAMP_RE,
                    'contact_person': version.metadata['contributor'][0]['name'],
                    'embargo_status': 'OPEN',
                    'star_count': 0,
                    'is_starred': False,
                },
                'version': version.version,
                'name': version.name,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                'asset_count': 0,
                'active_uploads': 0,
                'size': 0,
                'status': 'Pending',
            }
        ],
    }


@pytest.mark.django_db
def test_version_rest_retrieve(api_client, version, draft_version_factory):
    # Create an extra version so that there are multiple versions to filter down
    draft_version_factory()

    assert (
        api_client.get(
            f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/'
        ).data
        == version.metadata
    )


@pytest.mark.django_db
def test_version_rest_info(api_client, version):
    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/info/'
    ).data == {
        'dandiset': {
            'identifier': version.dandiset.identifier,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
            'contact_person': version.metadata['contributor'][0]['name'],
            'embargo_status': 'OPEN',
            'star_count': 0,
            'is_starred': False,
        },
        'version': version.version,
        'name': version.name,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'asset_count': 0,
        'active_uploads': 0,
        'metadata': version.metadata,
        'size': version.size,
        'status': 'Pending',
        'asset_validation_errors': [],
        'version_validation_errors': [],
        'contact_person': version.metadata['contributor'][0]['name'],
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    'asset_status',
    [Asset.Status.PENDING, Asset.Status.VALIDATING, Asset.Status.VALID, Asset.Status.INVALID],
)
def test_version_rest_info_with_asset(
    api_client, draft_version_factory, draft_asset_factory, asset_status: Asset.Status
):
    version = draft_version_factory(status=Version.Status.VALID)
    asset = draft_asset_factory(status=asset_status)
    version.assets.add(asset)
    add_version_asset_paths(version=version)

    # Create expected validation errors for pending/validating assets
    expected_validation_errors = (
        [
            {
                'field': '',
                'message': 'asset is currently being validated, please wait.',
                'path': asset.path,
            }
        ]
        if asset_status in [Asset.Status.PENDING, Asset.Status.VALIDATING]
        else []
    )

    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/info/'
    ).data == {
        'dandiset': {
            'identifier': version.dandiset.identifier,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
            'contact_person': version.metadata['contributor'][0]['name'],
            'embargo_status': 'OPEN',
            'star_count': 0,
            'is_starred': False,
        },
        'version': version.version,
        'name': version.name,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'asset_count': 1,
        'active_uploads': 0,
        'metadata': version.metadata,
        'size': version.size,
        'status': Asset.Status.VALID,
        'asset_validation_errors': expected_validation_errors,
        'version_validation_errors': [],
        'contact_person': version.metadata['contributor'][0]['name'],
    }


@pytest.mark.django_db
def test_version_rest_update(api_client, user, draft_version):
    add_dandiset_owner(draft_version.dandiset, user)
    api_client.force_authenticate(user=user)

    new_name = 'A unique and special name!'
    new_metadata = {
        '@context': (
            'https://raw.githubusercontent.com/dandi/schema/master/releases/'
            f'{settings.DANDI_SCHEMA_VERSION}/context.json'
        ),
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'foo': 'bar',
        'num': 123,
        'list': ['a', 'b', 'c'],
        'very_large': 'words' * 10,
        'contributor': [
            {
                'name': 'Vargas, Getúlio',
                'roleName': ['dcite:ContactPerson'],
                'schemaKey': 'Person',
            }
        ],
        # This should be stripped out
        'dateCreated': 'foobar',
    }
    year = datetime.datetime.now(datetime.UTC).year
    url = f'{settings.DANDI_WEB_APP_URL}/dandiset/{draft_version.dandiset.identifier}/draft'
    saved_metadata = {
        **new_metadata,
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'manifestLocation': [
            f'{settings.DANDI_API_URL}/api/dandisets/{draft_version.dandiset.identifier}/versions/draft/assets/'
        ],
        'name': new_name,
        'identifier': f'DANDI:{draft_version.dandiset.identifier}',
        'id': f'DANDI:{draft_version.dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'repository': settings.DANDI_WEB_APP_URL,
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'access': [{'schemaKey': 'AccessRequirements', 'status': AccessType.OpenAccess.value}],
        'citation': f'{new_name} ({year}). (Version draft) [Data set]. DANDI Archive. {url}',
        'assetsSummary': {
            'numberOfBytes': 0,
            'numberOfFiles': 0,
            'schemaKey': 'AssetsSummary',
        },
    }

    assert api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/versions/{draft_version.version}/',
        {'metadata': new_metadata, 'name': new_name},
        format='json',
    ).data == {
        'dandiset': {
            'identifier': draft_version.dandiset.identifier,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
            'contact_person': 'Vargas, Getúlio',
            'embargo_status': 'OPEN',
            'star_count': 0,
            'is_starred': False,
        },
        'version': draft_version.version,
        'name': new_name,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'asset_count': draft_version.asset_count,
        'active_uploads': draft_version.active_uploads,
        'metadata': saved_metadata,
        'size': draft_version.size,
        'status': 'Pending',
        'asset_validation_errors': [],
        'version_validation_errors': [],
        'contact_person': 'Vargas, Getúlio',
    }

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time

    assert draft_version.metadata == saved_metadata
    assert draft_version.name == new_name
    assert draft_version.status == Version.Status.PENDING


@pytest.mark.django_db
def test_version_rest_update_unembargo_in_progress(api_client, user, draft_version_factory):
    draft_version = draft_version_factory(
        dandiset__embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING
    )
    add_dandiset_owner(draft_version.dandiset, user)
    api_client.force_authenticate(user=user)

    new_name = 'A unique and special name!'
    new_metadata = {
        '@context': (
            'https://raw.githubusercontent.com/dandi/schema/master/releases/'
            f'{settings.DANDI_SCHEMA_VERSION}/context.json'
        ),
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'num': 123,
    }

    resp = api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/versions/{draft_version.version}/',
        {'metadata': new_metadata, 'name': new_name},
        format='json',
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_version_rest_update_published_version(api_client, user, published_version):
    add_dandiset_owner(published_version.dandiset, user)
    api_client.force_authenticate(user=user)

    new_name = 'A unique and special name!'
    new_metadata = {'foo': 'bar', 'num': 123, 'list': ['a', 'b', 'c']}

    resp = api_client.put(
        f'/api/dandisets/{published_version.dandiset.identifier}'
        f'/versions/{published_version.version}/',
        {'metadata': new_metadata, 'name': new_name},
        format='json',
    )
    assert resp.status_code == 405
    assert resp.data == 'Only draft versions can be modified.'


@pytest.mark.django_db
def test_version_rest_update_not_an_owner(api_client, user, version):
    api_client.force_authenticate(user=user)

    new_name = 'A unique and special name!'
    new_metadata = {'foo': 'bar', 'num': 123, 'list': ['a', 'b', 'c']}

    assert (
        api_client.put(
            f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/',
            {'metadata': new_metadata, 'name': new_name},
            format='json',
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    ('access'),
    [
        'some value',
        123,
        None,
        [],
        ['a', 'b'],
        ['a', 'b', {}],
        [{'schemaKey': 'AccessRequirements', 'status': 'foobar'}],
    ],
)
@pytest.mark.django_db
def test_version_rest_update_access_values(api_client, user, draft_version, access):
    add_dandiset_owner(draft_version.dandiset, user)
    api_client.force_authenticate(user=user)

    new_metadata = {**draft_version.metadata, 'access': access}
    resp = api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/versions/{draft_version.version}/',
        {'metadata': new_metadata, 'name': draft_version.name},
        format='json',
    )
    assert resp.status_code == 200
    draft_version.refresh_from_db()

    access = draft_version.metadata['access']
    assert access != new_metadata['access']
    assert access[0]['schemaKey'] == 'AccessRequirements'
    assert (
        access[0]['status'] == AccessType.EmbargoedAccess.value
        if draft_version.dandiset.embargoed
        else AccessType.OpenAccess.value
    )


@pytest.mark.django_db
def test_version_rest_update_access_missing(api_client, user, draft_version):
    add_dandiset_owner(draft_version.dandiset, user)
    api_client.force_authenticate(user=user)

    # Check that the field missing entirely is also okay
    new_metadata = {**draft_version.metadata}
    new_metadata.pop('access', None)

    resp = api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/versions/{draft_version.version}/',
        {'metadata': new_metadata, 'name': draft_version.name},
        format='json',
    )
    assert resp.status_code == 200
    draft_version.refresh_from_db()
    assert 'access' in draft_version.metadata
    access = draft_version.metadata['access']
    assert access[0]['schemaKey'] == 'AccessRequirements'
    assert (
        access[0]['status'] == AccessType.EmbargoedAccess.value
        if draft_version.dandiset.embargoed
        else AccessType.OpenAccess.value
    )


@pytest.mark.django_db
def test_version_rest_update_access_valid(api_client, user, draft_version):
    add_dandiset_owner(draft_version.dandiset, user)
    api_client.force_authenticate(user=user)

    # Check that extra fields persist
    new_metadata = {**draft_version.metadata, 'access': [{'extra': 'field'}]}
    resp = api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/versions/{draft_version.version}/',
        {'metadata': new_metadata, 'name': draft_version.name},
        format='json',
    )
    assert resp.status_code == 200
    draft_version.refresh_from_db()
    access = draft_version.metadata['access']
    assert access != new_metadata['access']
    assert access[0]['schemaKey'] == 'AccessRequirements'
    assert (
        access[0]['status'] == AccessType.EmbargoedAccess.value
        if draft_version.dandiset.embargoed
        else AccessType.OpenAccess.value
    )

    assert access[0]['extra'] == 'field'


@pytest.mark.django_db
def test_version_rest_publish(
    api_client: APIClient,
    user: User,
    draft_version: Version,
    draft_asset_factory,
    published_asset_factory,
):
    add_dandiset_owner(draft_version.dandiset, user)
    api_client.force_authenticate(user=user)

    old_draft_asset: Asset = draft_asset_factory()
    old_published_asset: Asset = published_asset_factory()
    assert not old_draft_asset.published
    assert old_published_asset.published
    draft_version.assets.add(old_draft_asset)
    draft_version.assets.add(old_published_asset)

    # Validate the metadata to mark the assets and version as `VALID`
    tasks.validate_asset_metadata_task(old_draft_asset.id)
    tasks.validate_version_metadata_task(draft_version.id)
    draft_version.refresh_from_db()
    assert draft_version.publishable

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/publish/'
    )
    assert resp.status_code == 202

    draft_version.refresh_from_db()
    assert draft_version.status == Version.Status.PUBLISHING


@pytest.mark.django_db
def test_version_rest_publish_embargo(api_client: APIClient, user: User, draft_version_factory):
    draft_version = draft_version_factory(dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    add_dandiset_owner(draft_version.dandiset, user)
    api_client.force_authenticate(user=user)

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/publish/'
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_version_rest_publish_unembargo_in_progress(
    api_client: APIClient, user: User, draft_version_factory
):
    draft_version = draft_version_factory(
        dandiset__embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING
    )
    add_dandiset_owner(draft_version.dandiset, user)
    api_client.force_authenticate(user=user)

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/publish/'
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_version_rest_publish_zarr(
    api_client,
    user: User,
    draft_version: Version,
    draft_asset_factory,
    zarr_archive_factory,
    zarr_file_factory,
):
    add_dandiset_owner(draft_version.dandiset, user)
    api_client.force_authenticate(user=user)

    # create and ingest zarr archive
    zarr_archive = zarr_archive_factory(dandiset=draft_version.dandiset, status='Uploaded')
    zarr_file_factory(zarr_archive=zarr_archive)
    ingest_zarr_archive(zarr_archive.zarr_id)
    zarr_archive.refresh_from_db()

    zarr_asset: Asset = draft_asset_factory(zarr=zarr_archive, blob=None)
    normal_asset: Asset = draft_asset_factory()
    draft_version.assets.add(zarr_asset)
    draft_version.assets.add(normal_asset)

    # Validate the metadata to mark the assets and version as `VALID`
    tasks.validate_asset_metadata_task(zarr_asset.id)
    tasks.validate_asset_metadata_task(normal_asset.id)
    tasks.validate_version_metadata_task(draft_version.id)
    draft_version.refresh_from_db()
    assert draft_version.publishable

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/publish/'
    )
    assert resp.status_code == 400
    assert resp.json() == 'Cannot publish dandisets which contain zarrs'


@pytest.mark.django_db
def test_version_rest_publish_not_an_owner(api_client, user, version, asset):
    api_client.force_authenticate(user=user)
    version.assets.add(asset)

    resp = api_client.post(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/publish/'
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_version_rest_publish_not_a_draft(api_client, user, published_version, asset):
    add_dandiset_owner(published_version.dandiset, user)
    api_client.force_authenticate(user=user)
    published_version.assets.add(asset)

    resp = api_client.post(
        f'/api/dandisets/{published_version.dandiset.identifier}'
        f'/versions/{published_version.version}/publish/'
    )
    assert resp.status_code == 405


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('status', 'expected_data', 'expected_status_code'),
    [
        (
            Version.Status.PENDING,
            'Metadata validation is pending for this dandiset, please try again later.',
            409,
        ),
        (Version.Status.VALIDATING, 'Dandiset is currently being validated', 409),
        (Version.Status.INVALID, 'Dandiset metadata or asset metadata is not valid', 400),
        (
            Version.Status.PUBLISHED,
            'There have been no changes to the draft version since the last publish.',
            400,
        ),
        (Version.Status.PUBLISHING, 'Dandiset is currently being published', 423),
    ],
)
def test_version_rest_publish_invalid(
    api_client: APIClient,
    user: User,
    draft_version: Version,
    asset: Asset,
    status: str,
    expected_data: str,
    expected_status_code: int,
):
    add_dandiset_owner(draft_version.dandiset, user)
    api_client.force_authenticate(user=user)
    draft_version.assets.add(asset)

    draft_version.status = status
    draft_version.save()

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/publish/'
    )
    assert resp.status_code == expected_status_code
    assert resp.data == expected_data


@pytest.mark.django_db
def test_version_rest_update_no_changed_metadata(
    api_client: APIClient, admin_user, draft_version: Version
):
    """Test that PUT'ing unchanged metadata doesn't trigger revalidation or DB modifications."""
    api_client.force_authenticate(user=admin_user)

    old_modified_time = draft_version.modified

    sleep(0.1)

    api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/versions/{draft_version.version}/',
        {'metadata': draft_version.metadata, 'name': draft_version.name},
        format='json',
    )

    draft_version.refresh_from_db()

    assert draft_version.modified == old_modified_time


@pytest.mark.django_db
def test_version_rest_delete_published_not_admin(api_client, user, published_version):
    add_dandiset_owner(published_version.dandiset, user)
    api_client.force_authenticate(user=user)
    response = api_client.delete(
        f'/api/dandisets/{published_version.dandiset.identifier}'
        f'/versions/{published_version.version}/'
    )
    assert response.status_code == 403
    assert response.data == 'Cannot delete published versions'
    assert published_version in Version.objects.all()


@pytest.mark.django_db
def test_version_rest_delete_published_admin(api_client, admin_user, published_version):
    api_client.force_authenticate(user=admin_user)
    response = api_client.delete(
        f'/api/dandisets/{published_version.dandiset.identifier}'
        f'/versions/{published_version.version}/'
    )
    assert response.status_code == 204
    assert not Version.objects.all()


@pytest.mark.django_db
def test_version_rest_delete_draft_not_admin(api_client, user, draft_version):
    add_dandiset_owner(draft_version.dandiset, user)
    api_client.force_authenticate(user=user)
    response = api_client.delete(
        f'/api/dandisets/{draft_version.dandiset.identifier}/versions/{draft_version.version}/'
    )
    assert response.status_code == 403
    assert response.data == 'Cannot delete draft versions'
    assert draft_version in Version.objects.all()


@pytest.mark.django_db
def test_version_rest_delete_draft_admin(api_client, admin_user, draft_version):
    api_client.force_authenticate(user=admin_user)
    response = api_client.delete(
        f'/api/dandisets/{draft_version.dandiset.identifier}/versions/{draft_version.version}/'
    )
    assert response.status_code == 403
    assert response.data == 'Cannot delete draft versions'
    assert draft_version in Version.objects.all()
