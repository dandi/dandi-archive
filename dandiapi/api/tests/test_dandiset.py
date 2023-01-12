from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api.asset_paths import add_asset_paths
from dandiapi.api.models import Dandiset, Version

from .fuzzy import DANDISET_ID_RE, DANDISET_SCHEMA_ID_RE, TIMESTAMP_RE, UTC_ISO_TIMESTAMP_RE


@pytest.mark.django_db
def test_dandiset_identifier(dandiset):
    assert int(dandiset.identifier) == dandiset.id


def test_dandiset_identifer_missing(dandiset_factory):
    dandiset = dandiset_factory.build()
    # This should have a sane fallback
    assert dandiset.identifier == ''


@pytest.mark.django_db
def test_dandiset_published_count(
    dandiset_factory, draft_version_factory, published_version_factory
):
    # empty dandiset
    dandiset_factory()
    # dandiset with draft version
    draft_version_factory(dandiset=dandiset_factory())
    # dandiset with published version
    published_version_factory(dandiset=dandiset_factory())

    assert Dandiset.published_count() == 1


@pytest.mark.parametrize(
    ('embargo_status', 'user_status', 'visible'),
    [
        ('OPEN', 'owner', True),
        ('OPEN', 'anonymous', True),
        ('OPEN', 'not-owner', True),
        ('EMBARGOED', 'owner', True),
        ('EMBARGOED', 'anonymous', False),
        ('EMBARGOED', 'not-owner', False),
        ('UNEMBARGOING', 'owner', True),
        ('UNEMBARGOING', 'anonymous', False),
        ('UNEMBARGOING', 'not-owner', False),
    ],
)
@pytest.mark.django_db
def test_dandiset_manager_visible_to(
    dandiset_factory, user_factory, embargo_status, user_status, visible
):
    dandiset = dandiset_factory(embargo_status=embargo_status)
    if user_status == 'anonymous':
        user = AnonymousUser
    else:
        user = user_factory()
    if user_status == 'owner':
        assign_perm('owner', user, dandiset)

    assert list(Dandiset.objects.visible_to(user)) == ([dandiset] if visible else [])


@pytest.mark.django_db
def test_dandiset_rest_list(api_client, dandiset):
    assert api_client.get('/api/dandisets/', {'draft': 'true', 'empty': 'true'}).json() == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'identifier': dandiset.identifier,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                'draft_version': None,
                'most_recent_published_version': None,
                'contact_person': '',
                'embargo_status': 'OPEN',
            }
        ],
    }


@pytest.mark.parametrize(
    ('params', 'results'),
    [
        ('', ['empty', 'draft', 'published', 'erased']),
        ('?draft=false', ['published', 'erased']),
        ('?empty=false', ['draft', 'published']),
        ('?draft=true&empty=true', ['empty', 'draft', 'published', 'erased']),
        ('?empty=true&draft=true', ['empty', 'draft', 'published', 'erased']),
        ('?draft=false&empty=false', ['published']),
    ],
    ids=[
        'nothing',
        'empty-only',
        'draft-only',
        'draft-empty',
        'empty-draft',
        'draft-false-empty-false',
    ],
)
@pytest.mark.django_db
def test_dandiset_versions(
    api_client,
    dandiset_factory,
    draft_version_factory,
    published_version_factory,
    asset_factory,
    params,
    results,
):
    # Create some dandisets of different kinds.
    #
    # Dandiset with empty draft
    empty_dandiset = dandiset_factory()
    draft_version_factory(dandiset=empty_dandiset)

    # Dandiset with populated draft
    draft_dandiset = dandiset_factory()
    draft_version = draft_version_factory(dandiset=draft_dandiset)
    draft_version.assets.add(asset_factory())

    # Dandiset with published version
    published_dandiset = dandiset_factory()
    draft_version = draft_version_factory(dandiset=published_dandiset)
    draft_version.assets.add(asset_factory())
    published_version = published_version_factory(dandiset=published_dandiset)
    published_version.assets.add(asset_factory())

    # Dandiset with published version and empty draft
    erased_dandiset = dandiset_factory()
    draft_version_factory(dandiset=erased_dandiset)
    published_version = published_version_factory(dandiset=erased_dandiset)
    published_version.assets.add(asset_factory())

    def expected_serialization(dandiset: Dandiset):
        draft_version = dandiset.draft_version
        published_version = dandiset.most_recent_published_version
        contact_person = (published_version or draft_version).metadata['contributor'][0]['name']
        return {
            'identifier': dandiset.identifier,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
            'contact_person': contact_person,
            'embargo_status': 'OPEN',
            'draft_version': {
                'version': draft_version.version,
                'name': draft_version.name,
                'asset_count': draft_version.asset_count,
                'size': draft_version.size,
                'status': 'Pending',
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
            }
            if draft_version is not None
            else None,
            'most_recent_published_version': {
                'version': published_version.version,
                'name': published_version.name,
                'asset_count': published_version.asset_count,
                'size': published_version.size,
                'status': 'Pending',
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
            }
            if published_version is not None
            else None,
        }

    possible_results = {
        'empty': expected_serialization(empty_dandiset),
        'draft': expected_serialization(draft_dandiset),
        'published': expected_serialization(published_dandiset),
        'erased': expected_serialization(erased_dandiset),
    }

    expected_results = [possible_results[result] for result in results]

    assert api_client.get(f'/api/dandisets/{params}').json() == {
        'count': len(results),
        'next': None,
        'previous': None,
        'results': expected_results,
    }


@pytest.mark.django_db
def test_dandiset_rest_list_for_user(api_client, user, dandiset_factory):
    dandiset = dandiset_factory()
    # Create an extra dandiset that should not be included in the response
    dandiset_factory()
    api_client.force_authenticate(user=user)
    assign_perm('owner', user, dandiset)
    assert api_client.get('/api/dandisets/?user=me&draft=true&empty=true').data == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'identifier': dandiset.identifier,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                'draft_version': None,
                'most_recent_published_version': None,
                'contact_person': '',
                'embargo_status': 'OPEN',
            }
        ],
    }


@pytest.mark.django_db
def test_dandiset_rest_retrieve(api_client, dandiset):
    assert api_client.get(f'/api/dandisets/{dandiset.identifier}/').data == {
        'identifier': dandiset.identifier,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'draft_version': None,
        'most_recent_published_version': None,
        'contact_person': '',
        'embargo_status': 'OPEN',
    }


@pytest.mark.parametrize(
    ('embargo_status'),
    [choice[0] for choice in Dandiset.EmbargoStatus.choices],
    ids=[choice[1] for choice in Dandiset.EmbargoStatus.choices],
)
@pytest.mark.django_db
def test_dandiset_rest_embargo_access(
    api_client, user_factory, dandiset_factory, embargo_status: str
):
    owner = user_factory()
    unauthorized_user = user_factory()
    dandiset = dandiset_factory(embargo_status=embargo_status)
    assign_perm('owner', owner, dandiset)

    # This is what authorized users should get from the retrieve endpoint
    expected_dandiset_serialization = {
        'identifier': dandiset.identifier,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'draft_version': None,
        'most_recent_published_version': None,
        'contact_person': '',
        'embargo_status': embargo_status,
    }
    # This is what unauthorized users should get from the retrieve endpoint
    expected_error_message = {'detail': 'Not found.'}
    # This is what authorized users should get from the list endpoint
    expected_visible_pagination = {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [expected_dandiset_serialization],
    }
    # This is what unauthorized users should get from the list endpoint
    expected_invisible_pagination = {
        'count': 0,
        'next': None,
        'previous': None,
        'results': [],
    }

    # Anonymous users should only be able to access OPEN dandisets
    assert (
        api_client.get(f'/api/dandisets/{dandiset.identifier}/').json()
        == expected_dandiset_serialization
        if embargo_status == 'OPEN'
        else expected_error_message
    )
    assert (
        api_client.get('/api/dandisets/').json() == expected_visible_pagination
        if embargo_status == 'OPEN'
        else expected_invisible_pagination
    )

    # An unauthorized user should only be able to access OPEN dandisets
    api_client.force_authenticate(user=unauthorized_user)
    assert (
        api_client.get(f'/api/dandisets/{dandiset.identifier}/').json()
        == expected_dandiset_serialization
        if embargo_status == 'OPEN'
        else expected_error_message
    )
    assert (
        api_client.get('/api/dandisets/').json() == expected_visible_pagination
        if embargo_status == 'OPEN'
        else expected_invisible_pagination
    )

    # The owner should always be able to access the dandiset
    api_client.force_authenticate(user=owner)
    assert (
        api_client.get(f'/api/dandisets/{dandiset.identifier}/').json()
        == expected_dandiset_serialization
    )
    assert api_client.get('/api/dandisets/').json() == expected_visible_pagination


@pytest.mark.django_db
def test_dandiset_rest_create(api_client, user):
    user.first_name = 'John'
    user.last_name = 'Doe'
    user.save()
    api_client.force_authenticate(user=user)
    name = 'Test Dandiset'
    metadata = {'foo': 'bar'}

    response = api_client.post(
        '/api/dandisets/', {'name': name, 'metadata': metadata}, format='json'
    )
    assert response.data == {
        'identifier': DANDISET_ID_RE,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'contact_person': 'Doe, John',
        'embargo_status': 'OPEN',
        'draft_version': {
            'version': 'draft',
            'name': name,
            'asset_count': 0,
            'size': 0,
            'dandiset': {
                'identifier': DANDISET_ID_RE,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                'contact_person': 'Doe, John',
                'embargo_status': 'OPEN',
            },
            'status': 'Pending',
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'most_recent_published_version': None,
    }
    id = int(response.data['identifier'])

    # Creating a Dandiset has side affects.
    # Verify that the user is the only owner.
    dandiset = Dandiset.objects.get(id=id)
    assert list(dandiset.owners.all()) == [user]

    # Verify that a draft Version and VersionMetadata were also created.
    assert dandiset.versions.count() == 1
    assert dandiset.most_recent_published_version is None
    assert dandiset.draft_version.version == 'draft'
    assert dandiset.draft_version.name == name
    assert dandiset.draft_version.status == Version.Status.PENDING

    # Verify that computed metadata was injected
    year = datetime.now().year
    url = f'{settings.DANDI_WEB_APP_URL}/dandiset/{dandiset.identifier}/draft'
    assert dandiset.draft_version.metadata == {
        **metadata,
        'manifestLocation': [
            f'{settings.DANDI_API_URL}/api/dandisets/{dandiset.identifier}/versions/draft/assets/'  # noqa: E501
        ],
        'name': name,
        'identifier': DANDISET_SCHEMA_ID_RE,
        'id': f'DANDI:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'citation': (
            f'{user.last_name}, {user.first_name} ({year}) {name} '
            f'(Version draft) [Data set]. DANDI archive. {url}'
        ),
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',  # noqa: E501
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'schemaKey': 'Dandiset',
        'access': [{'schemaKey': 'AccessRequirements', 'status': 'dandi:OpenAccess'}],
        'repository': settings.DANDI_WEB_APP_URL,
        'contributor': [
            {
                'name': 'Doe, John',
                'email': user.email,
                'roleName': ['dcite:ContactPerson'],
                'schemaKey': 'Person',
                'affiliation': [],
                'includeInCitation': True,
            }
        ],
        'assetsSummary': {
            'schemaKey': 'AssetsSummary',
            'numberOfBytes': 0,
            'numberOfFiles': 0,
        },
    }


@pytest.mark.django_db
def test_dandiset_rest_create_with_identifier(api_client, admin_user):
    admin_user.first_name = 'John'
    admin_user.last_name = 'Doe'
    admin_user.save()
    api_client.force_authenticate(user=admin_user)
    name = 'Test Dandiset'
    identifier = '123456'
    metadata = {'foo': 'bar', 'identifier': f'DANDI:{identifier}'}

    response = api_client.post(
        '/api/dandisets/',
        {'name': name, 'metadata': metadata},
        format='json',
    )
    assert response.data == {
        'identifier': identifier,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'most_recent_published_version': None,
        'draft_version': {
            'version': 'draft',
            'name': name,
            'asset_count': 0,
            'size': 0,
            'dandiset': {
                'identifier': identifier,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                'contact_person': 'Doe, John',
                'embargo_status': 'OPEN',
            },
            'status': 'Pending',
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'contact_person': 'Doe, John',
        'embargo_status': 'OPEN',
    }

    # Creating a Dandiset has side affects.
    # Verify that the user is the only owner.
    dandiset = Dandiset.objects.get(id=identifier)
    assert list(dandiset.owners.all()) == [admin_user]

    # Verify that a draft Version and VersionMetadata were also created.
    assert dandiset.versions.count() == 1
    assert dandiset.most_recent_published_version is None
    assert dandiset.draft_version.version == 'draft'
    assert dandiset.draft_version.name == name
    assert dandiset.draft_version.status == Version.Status.PENDING

    # Verify that computed metadata was injected
    year = datetime.now().year
    url = f'{settings.DANDI_WEB_APP_URL}/dandiset/{dandiset.identifier}/draft'
    assert dandiset.draft_version.metadata == {
        **metadata,
        'manifestLocation': [
            f'{settings.DANDI_API_URL}/api/dandisets/{dandiset.identifier}/versions/draft/assets/'  # noqa: E501
        ],
        'name': name,
        'identifier': f'DANDI:{identifier}',
        'id': f'DANDI:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'citation': (
            f'{admin_user.last_name}, {admin_user.first_name} ({year}) {name} '
            f'(Version draft) [Data set]. DANDI archive. {url}'
        ),
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',  # noqa: E501
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'schemaKey': 'Dandiset',
        'access': [{'schemaKey': 'AccessRequirements', 'status': 'dandi:OpenAccess'}],
        'repository': settings.DANDI_WEB_APP_URL,
        'contributor': [
            {
                'name': 'Doe, John',
                'email': admin_user.email,
                'roleName': ['dcite:ContactPerson'],
                'schemaKey': 'Person',
                'affiliation': [],
                'includeInCitation': True,
            }
        ],
        'assetsSummary': {
            'schemaKey': 'AssetsSummary',
            'numberOfBytes': 0,
            'numberOfFiles': 0,
        },
    }


@pytest.mark.django_db
def test_dandiset_rest_create_with_contributor(api_client, admin_user):
    admin_user.first_name = 'John'
    admin_user.last_name = 'Doe'
    admin_user.save()
    api_client.force_authenticate(user=admin_user)
    name = 'Test Dandiset'
    identifier = '123456'
    metadata = {
        'foo': 'bar',
        'identifier': f'DANDI:{identifier}',
        # This contributor is different from the admin_user
        'contributor': [
            {
                'name': 'Jane Doe',
                'email': 'jane.doe@kitware.com',
                'roleName': ['dcite:ContactPerson'],
                'schemaKey': 'Person',
                'affiliation': [],
                'includeInCitation': True,
            }
        ],
    }

    response = api_client.post(
        '/api/dandisets/',
        {'name': name, 'metadata': metadata},
        format='json',
    )
    assert response.data == {
        'identifier': identifier,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'most_recent_published_version': None,
        'draft_version': {
            'version': 'draft',
            'name': name,
            'asset_count': 0,
            'size': 0,
            'dandiset': {
                'identifier': identifier,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                'contact_person': 'Jane Doe',
                'embargo_status': 'OPEN',
            },
            'status': 'Pending',
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'contact_person': 'Jane Doe',
        'embargo_status': 'OPEN',
    }

    # Creating a Dandiset has side affects.
    # Verify that the user is the only owner.
    dandiset = Dandiset.objects.get(id=identifier)
    assert list(dandiset.owners.all()) == [admin_user]

    # Verify that a draft Version and VersionMetadata were also created.
    assert dandiset.versions.count() == 1
    assert dandiset.most_recent_published_version is None
    assert dandiset.draft_version.version == 'draft'
    assert dandiset.draft_version.name == name
    assert dandiset.draft_version.status == Version.Status.PENDING

    # Verify that computed metadata was injected
    year = datetime.now().year
    url = f'{settings.DANDI_WEB_APP_URL}/dandiset/{dandiset.identifier}/draft'
    assert dandiset.draft_version.metadata == {
        **metadata,
        'manifestLocation': [
            f'{settings.DANDI_API_URL}/api/dandisets/{dandiset.identifier}/versions/draft/assets/'  # noqa: E501
        ],
        'name': name,
        'identifier': f'DANDI:{identifier}',
        'id': f'DANDI:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'citation': (
            f'Jane Doe ({year}) {name} ' f'(Version draft) [Data set]. DANDI archive. {url}'
        ),
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',  # noqa: E501
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'schemaKey': 'Dandiset',
        'access': [{'schemaKey': 'AccessRequirements', 'status': 'dandi:OpenAccess'}],
        'repository': settings.DANDI_WEB_APP_URL,
        'contributor': [
            {
                'name': 'Jane Doe',
                'email': 'jane.doe@kitware.com',
                'roleName': ['dcite:ContactPerson'],
                'schemaKey': 'Person',
                'affiliation': [],
                'includeInCitation': True,
            }
        ],
        'assetsSummary': {
            'schemaKey': 'AssetsSummary',
            'numberOfBytes': 0,
            'numberOfFiles': 0,
        },
    }


@pytest.mark.django_db
def test_dandiset_rest_create_embargoed(api_client, user):
    user.first_name = 'John'
    user.last_name = 'Doe'
    user.save()
    api_client.force_authenticate(user=user)
    name = 'Test Dandiset'
    metadata = {'foo': 'bar'}

    response = api_client.post(
        '/api/dandisets/?embargo=true', {'name': name, 'metadata': metadata}, format='json'
    )
    assert response.data == {
        'identifier': DANDISET_ID_RE,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'contact_person': 'Doe, John',
        'embargo_status': 'EMBARGOED',
        'draft_version': {
            'version': 'draft',
            'name': name,
            'asset_count': 0,
            'size': 0,
            'dandiset': {
                'identifier': DANDISET_ID_RE,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                'contact_person': 'Doe, John',
                'embargo_status': 'EMBARGOED',
            },
            'status': 'Pending',
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'most_recent_published_version': None,
    }
    id = int(response.data['identifier'])

    # Creating a Dandiset has side affects.
    # Verify that the user is the only owner.
    dandiset = Dandiset.objects.get(id=id)
    assert list(dandiset.owners.all()) == [user]

    # Verify that a draft Version and VersionMetadata were also created.
    assert dandiset.versions.count() == 1
    assert dandiset.most_recent_published_version is None
    assert dandiset.draft_version.version == 'draft'
    assert dandiset.draft_version.name == name
    assert dandiset.draft_version.status == Version.Status.PENDING

    # Verify that computed metadata was injected
    year = datetime.now().year
    url = f'{settings.DANDI_WEB_APP_URL}/dandiset/{dandiset.identifier}/draft'
    assert dandiset.draft_version.metadata == {
        **metadata,
        'manifestLocation': [
            f'{settings.DANDI_API_URL}/api/dandisets/{dandiset.identifier}/versions/draft/assets/'  # noqa: E501
        ],
        'name': name,
        'identifier': DANDISET_SCHEMA_ID_RE,
        'id': f'DANDI:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'citation': (
            f'{user.last_name}, {user.first_name} ({year}) {name} '
            f'(Version draft) [Data set]. DANDI archive. {url}'
        ),
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',  # noqa: E501
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'schemaKey': 'Dandiset',
        'access': [{'schemaKey': 'AccessRequirements', 'status': 'dandi:EmbargoedAccess'}],
        'repository': settings.DANDI_WEB_APP_URL,
        'contributor': [
            {
                'name': 'Doe, John',
                'email': user.email,
                'roleName': ['dcite:ContactPerson'],
                'schemaKey': 'Person',
                'affiliation': [],
                'includeInCitation': True,
            }
        ],
        'assetsSummary': {
            'schemaKey': 'AssetsSummary',
            'numberOfBytes': 0,
            'numberOfFiles': 0,
        },
    }


@pytest.mark.django_db
def test_dandiset_rest_create_with_duplicate_identifier(api_client, admin_user, dandiset):
    api_client.force_authenticate(user=admin_user)
    name = 'Test Dandiset'
    identifier = dandiset.identifier
    metadata = {'foo': 'bar', 'identifier': f'DANDI:{identifier}'}

    response = api_client.post(
        '/api/dandisets/',
        {'name': name, 'metadata': metadata},
        format='json',
    )
    assert response.status_code == 400
    assert response.data == f'Dandiset {identifier} already exists'


@pytest.mark.django_db
def test_dandiset_rest_create_with_invalid_identifier(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    name = 'Test Dandiset'
    identifier = 'abc123'
    metadata = {'foo': 'bar', 'identifier': identifier}

    response = api_client.post(
        '/api/dandisets/',
        {'name': name, 'metadata': metadata},
        format='json',
    )
    assert response.status_code == 400
    assert response.data == f'Invalid Identifier {identifier}'


@pytest.mark.parametrize(
    ('embargo_status'),
    [choice[0] for choice in Dandiset.EmbargoStatus.choices],
    ids=[choice[1] for choice in Dandiset.EmbargoStatus.choices],
)
@pytest.mark.django_db
def test_dandiset_rest_delete(api_client, draft_version_factory, user, embargo_status):
    draft_version = draft_version_factory(dandiset__embargo_status=embargo_status)
    api_client.force_authenticate(user=user)
    assign_perm('owner', user, draft_version.dandiset)

    response = api_client.delete(f'/api/dandisets/{draft_version.dandiset.identifier}/')
    assert response.status_code == 204

    assert not Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_delete_with_zarrs(
    api_client,
    draft_version,
    user,
    zarr_archive_factory,
    draft_asset_factory,
):
    api_client.force_authenticate(user=user)
    assign_perm('owner', user, draft_version.dandiset)
    zarr = zarr_archive_factory(dandiset=draft_version.dandiset)
    asset = draft_asset_factory(blob=None, embargoed_blob=None, zarr=zarr)

    # Add paths
    add_asset_paths(asset=asset, version=draft_version)

    # Delete
    response = api_client.delete(f'/api/dandisets/{draft_version.dandiset.identifier}/')
    assert response.status_code == 204
    assert not Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_delete_not_an_owner(api_client, draft_version, user):
    api_client.force_authenticate(user=user)

    response = api_client.delete(f'/api/dandisets/{draft_version.dandiset.identifier}/')
    assert response.status_code == 403

    assert draft_version.dandiset in Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_delete_published(api_client, published_version, user):
    api_client.force_authenticate(user=user)
    assign_perm('owner', user, published_version.dandiset)

    response = api_client.delete(f'/api/dandisets/{published_version.dandiset.identifier}/')
    assert response.status_code == 403
    assert response.data == 'Cannot delete dandisets with published versions.'

    assert published_version.dandiset in Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_delete_published_admin(api_client, published_version, admin_user):
    api_client.force_authenticate(user=admin_user)

    response = api_client.delete(f'/api/dandisets/{published_version.dandiset.identifier}/')
    assert response.status_code == 403
    assert response.data == 'Cannot delete dandisets with published versions.'

    assert published_version.dandiset in Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_get_owners(api_client, dandiset, social_account):
    assign_perm('owner', social_account.user, dandiset)

    resp = api_client.get(f'/api/dandisets/{dandiset.identifier}/users/')

    assert resp.status_code == 200
    assert resp.data == [
        {
            'username': social_account.extra_data['login'],
            'name': social_account.extra_data['name'],
        }
    ]


@pytest.mark.django_db
def test_dandiset_rest_get_owners_no_social_account(api_client, dandiset, user):
    assign_perm('owner', user, dandiset)

    resp = api_client.get(f'/api/dandisets/{dandiset.identifier}/users/')

    assert resp.status_code == 200
    assert resp.data == [{'username': user.username, 'name': f'{user.first_name} {user.last_name}'}]


@pytest.mark.django_db
def test_dandiset_rest_change_owner(
    api_client,
    draft_version,
    user_factory,
    social_account_factory,
    mailoutbox,
):
    dandiset = draft_version.dandiset
    user1 = user_factory()
    user2 = user_factory()
    social_account2 = social_account_factory(user=user2)
    assign_perm('owner', user1, dandiset)
    api_client.force_authenticate(user=user1)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': social_account2.extra_data['login']}],
        format='json',
    )

    assert resp.status_code == 200
    assert resp.data == [
        {
            'username': social_account2.extra_data['login'],
            'name': social_account2.extra_data['name'],
        }
    ]
    assert list(dandiset.owners) == [user2]

    assert len(mailoutbox) == 2
    assert mailoutbox[0].subject == f'Removed from Dandiset "{dandiset.draft_version.name}"'
    assert mailoutbox[0].to == [user1.email]
    assert mailoutbox[1].subject == f'Added to Dandiset "{dandiset.draft_version.name}"'
    assert mailoutbox[1].to == [user2.email]


@pytest.mark.django_db
def test_dandiset_rest_add_owner(
    api_client,
    draft_version,
    user_factory,
    social_account_factory,
    mailoutbox,
):
    dandiset = draft_version.dandiset
    user1 = user_factory()
    user2 = user_factory()
    social_account1 = social_account_factory(user=user1)
    social_account2 = social_account_factory(user=user2)
    assign_perm('owner', user1, dandiset)
    api_client.force_authenticate(user=user1)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [
            {'username': social_account1.extra_data['login']},
            {'username': social_account2.extra_data['login']},
        ],
        format='json',
    )

    assert resp.status_code == 200
    assert resp.data == [
        {
            'username': social_account1.extra_data['login'],
            'name': social_account1.extra_data['name'],
        },
        {
            'username': social_account2.extra_data['login'],
            'name': social_account2.extra_data['name'],
        },
    ]
    assert list(dandiset.owners) == [user1, user2]

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == f'Added to Dandiset "{dandiset.draft_version.name}"'
    assert mailoutbox[0].to == [user2.email]


@pytest.mark.django_db
def test_dandiset_rest_remove_owner(
    api_client,
    draft_version,
    user_factory,
    social_account_factory,
    mailoutbox,
):
    dandiset = draft_version.dandiset
    user1 = user_factory()
    user2 = user_factory()
    social_account1 = social_account_factory(user=user1)
    assign_perm('owner', user1, dandiset)
    assign_perm('owner', user2, dandiset)
    api_client.force_authenticate(user=user1)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': social_account1.extra_data['login']}],
        format='json',
    )

    assert resp.status_code == 200
    assert resp.data == [
        {
            'username': social_account1.extra_data['login'],
            'name': social_account1.extra_data['name'],
        }
    ]
    assert list(dandiset.owners) == [user1]

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == f'Removed from Dandiset "{dandiset.draft_version.name}"'
    assert mailoutbox[0].to == [user2.email]


@pytest.mark.django_db
def test_dandiset_rest_not_an_owner(api_client, dandiset, user):
    api_client.force_authenticate(user=user)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': user.username}],
        format='json',
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dandiset_rest_delete_all_owners_fails(api_client, dandiset, user):
    assign_perm('owner', user, dandiset)
    api_client.force_authenticate(user=user)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [],
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == ['Cannot remove all draft owners']


@pytest.mark.django_db
def test_dandiset_rest_add_owner_does_not_exist(api_client, dandiset, user):
    assign_perm('owner', user, dandiset)
    api_client.force_authenticate(user=user)
    fake_name = user.username + 'butnotreally'

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': fake_name}],
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == [f'User {fake_name} not found']


@pytest.mark.django_db
def test_dandiset_rest_add_malformed(api_client, dandiset, user):
    assign_perm('owner', user, dandiset)
    api_client.force_authenticate(user=user)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'email': user.email}],
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == [{'username': ['This field is required.']}]


@pytest.mark.django_db
def test_dandiset_rest_search_no_query(api_client):
    assert api_client.get('/api/dandisets/').data['results'] == []


@pytest.mark.django_db
def test_dandiset_rest_search_empty_query(api_client):
    assert api_client.get('/api/dandisets/', {'search': ''}).data['results'] == []


@pytest.mark.django_db
def test_dandiset_rest_search_identifier(api_client, draft_version):
    results = api_client.get(
        '/api/dandisets/',
        {'search': draft_version.dandiset.identifier, 'draft': 'true', 'empty': 'true'},
    ).data['results']
    assert len(results) == 1
    assert results[0]['identifier'] == draft_version.dandiset.identifier

    assert results[0]['most_recent_published_version'] is None

    assert results[0]['draft_version']['version'] == draft_version.version
    assert results[0]['draft_version']['name'] == draft_version.name
