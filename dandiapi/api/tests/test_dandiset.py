from __future__ import annotations

import datetime
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
import pytest

from dandiapi.api.asset_paths import add_asset_paths, add_version_asset_paths
from dandiapi.api.models import Dandiset, Version
from dandiapi.api.services.permissions.dandiset import (
    get_dandiset_owners,
    get_visible_dandisets,
)
from dandiapi.api.tests.factories import DandisetFactory, UserFactory

from .fuzzy import (
    DANDISET_ID_RE,
    DANDISET_SCHEMA_ID_RE,
    DATE_RE,
    TIMESTAMP_RE,
    UTC_ISO_TIMESTAMP_RE,
)

if TYPE_CHECKING:
    from rest_framework.test import APIClient


@pytest.mark.django_db
def test_dandiset_identifier():
    dandiset = DandisetFactory.create()
    assert int(dandiset.identifier) == dandiset.id


def test_dandiset_identifer_missing():
    dandiset = DandisetFactory.build()
    # This should have a sane fallback
    assert dandiset.identifier == ''


@pytest.mark.django_db
def test_dandiset_published_count(draft_version_factory, published_version_factory):
    # empty dandiset
    DandisetFactory.create()
    # dandiset with draft version
    draft_version_factory(dandiset=DandisetFactory.create())
    # dandiset with published version
    published_version_factory(dandiset=DandisetFactory.create())

    assert Dandiset.published_count() == 1


@pytest.mark.parametrize(
    ('embargo_status', 'visible'),
    [
        ('OPEN', True),
        ('EMBARGOED', False),
        ('UNEMBARGOING', False),
    ],
)
@pytest.mark.django_db
def test_dandiset_get_visible_dandisets_anonymous(embargo_status: str, visible: bool):  # noqa: FBT001
    user = AnonymousUser()
    dandiset = DandisetFactory.create(embargo_status=embargo_status)

    assert list(get_visible_dandisets(user)) == ([dandiset] if visible else [])


@pytest.mark.parametrize(
    ('embargo_status', 'visible'),
    [
        ('OPEN', True),
        ('EMBARGOED', False),
        ('UNEMBARGOING', False),
    ],
)
@pytest.mark.django_db
def test_dandiset_get_visible_dandisets_nonowner(embargo_status: str, visible: bool):  # noqa: FBT001
    user = UserFactory.create()
    dandiset = DandisetFactory.create(embargo_status=embargo_status)

    assert list(get_visible_dandisets(user)) == ([dandiset] if visible else [])


@pytest.mark.parametrize(
    'embargo_status',
    [
        'OPEN',
        'EMBARGOED',
        'UNEMBARGOING',
    ],
)
@pytest.mark.django_db
def test_dandiset_get_visible_dandisets_owner(embargo_status: str):
    user = UserFactory.create()
    dandiset = DandisetFactory.create(embargo_status=embargo_status, owners=[user])

    assert list(get_visible_dandisets(user)) == [dandiset]


@pytest.mark.django_db
def test_dandiset_rest_list(api_client):
    user = UserFactory.create()
    dandiset = DandisetFactory.create()
    # Test un-authenticated request
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
                'star_count': 0,
                'is_starred': False,
            }
        ],
    }

    # Test request for embargoed dandisets while still un-authenticated
    r = api_client.get('/api/dandisets/', {'draft': 'true', 'empty': 'true', 'embargoed': 'true'})
    assert r.status_code == 401

    # Test request for embargoed dandisets after authenticated
    api_client.force_authenticate(user=user)
    r = api_client.get('/api/dandisets/', {'draft': 'true', 'empty': 'true', 'embargoed': 'true'})
    assert r.status_code == 200


@pytest.mark.parametrize(
    ('params', 'results'),
    [
        ('', ['empty', 'draft', 'published', 'erased']),
        ('?draft=false', ['published', 'erased']),
        ('?empty=false', ['draft', 'published', 'erased']),
        ('?draft=true&empty=true', ['empty', 'draft', 'published', 'erased']),
        ('?empty=true&draft=true', ['empty', 'draft', 'published', 'erased']),
        ('?draft=false&empty=false', ['published', 'erased']),
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
    draft_version_factory,
    published_version_factory,
    asset_factory,
    params,
    results,
):
    # Create some dandisets of different kinds.
    #
    # Dandiset with empty draft
    empty_dandiset = DandisetFactory.create()
    draft_version_factory(dandiset=empty_dandiset)

    # Dandiset with populated draft
    draft_dandiset = DandisetFactory.create()
    draft_version = draft_version_factory(dandiset=draft_dandiset)
    draft_version.assets.add(asset_factory())
    add_version_asset_paths(draft_version)

    # Dandiset with published version
    published_dandiset = DandisetFactory.create()
    draft_version = draft_version_factory(dandiset=published_dandiset)
    draft_version.assets.add(asset_factory())
    add_version_asset_paths(draft_version)

    published_version = published_version_factory(dandiset=published_dandiset)
    published_version.assets.add(asset_factory())
    add_version_asset_paths(published_version)

    # Dandiset with published version and empty draft
    erased_dandiset = DandisetFactory.create()
    draft_version_factory(dandiset=erased_dandiset)
    published_version = published_version_factory(dandiset=erased_dandiset)
    published_version.assets.add(asset_factory())
    add_version_asset_paths(published_version)

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
            'star_count': 0,
            'is_starred': False,
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
                'status': 'Published',
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
def test_dandiset_rest_list_for_user(api_client):
    user = UserFactory.create()
    dandiset = DandisetFactory.create(owners=[user])
    # Create an extra dandiset that should not be included in the response
    DandisetFactory.create()
    api_client.force_authenticate(user=user)
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
                'star_count': 0,
                'is_starred': False,
            }
        ],
    }


@pytest.mark.django_db
def test_dandiset_rest_retrieve(api_client):
    dandiset = DandisetFactory.create()
    assert api_client.get(f'/api/dandisets/{dandiset.identifier}/').data == {
        'identifier': dandiset.identifier,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'draft_version': None,
        'most_recent_published_version': None,
        'contact_person': '',
        'embargo_status': 'OPEN',
        'star_count': 0,
        'is_starred': False,
    }


@pytest.mark.django_db
def test_dandiset_rest_retrieve_embargoed_anonymous(api_client):
    dandiset: Dandiset = DandisetFactory.create(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)

    resp = api_client.get(f'/api/dandisets/{dandiset.identifier}/')
    assert resp.status_code == 401


@pytest.mark.django_db
def test_dandiset_rest_retrieve_embargoed_nonowner(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    dandiset: Dandiset = DandisetFactory.create(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)

    resp = api_client.get(f'/api/dandisets/{dandiset.identifier}/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dandiset_rest_retrieve_embargoed_owner(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    dandiset: Dandiset = DandisetFactory.create(
        embargo_status=Dandiset.EmbargoStatus.EMBARGOED, owners=[user]
    )

    resp = api_client.get(f'/api/dandisets/{dandiset.identifier}/')
    assert resp.status_code == 200


@pytest.mark.parametrize(
    ('embargo_status'),
    [choice[0] for choice in Dandiset.EmbargoStatus.choices],
    ids=[choice[1] for choice in Dandiset.EmbargoStatus.choices],
)
@pytest.mark.django_db
def test_dandiset_rest_embargo_access(api_client, embargo_status: str):
    owner = UserFactory.create()
    unauthorized_user = UserFactory.create()
    dandiset = DandisetFactory.create(embargo_status=embargo_status, owners=[owner])

    # This is what authorized users should get from the retrieve endpoint
    expected_dandiset_serialization = {
        'identifier': dandiset.identifier,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'draft_version': None,
        'most_recent_published_version': None,
        'contact_person': '',
        'embargo_status': embargo_status,
        'star_count': 0,
        'is_starred': False,
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
    assert (
        api_client.get('/api/dandisets/', {'embargoed': 'true'}).json()
        == expected_visible_pagination
    )


@pytest.mark.django_db
def test_dandiset_rest_create(api_client):
    user = UserFactory.create(first_name='John', last_name='Doe')
    api_client.force_authenticate(user=user)
    name = 'Test Dandiset'
    metadata = {'foo': 'bar'}

    response = api_client.post('/api/dandisets/', {'name': name, 'metadata': metadata})
    assert response.data == {
        'identifier': DANDISET_ID_RE,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'contact_person': 'Doe, John',
        'embargo_status': 'OPEN',
        'star_count': 0,
        'is_starred': False,
        'draft_version': {
            'version': 'draft',
            'name': name,
            'asset_count': 0,
            'active_uploads': 0,
            'size': 0,
            'status': 'Pending',
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'most_recent_published_version': None,
    }
    dandiset_id = int(response.data['identifier'])

    # Creating a Dandiset has side affects.
    # Verify that the user is the only owner.
    dandiset = Dandiset.objects.get(id=dandiset_id)
    assert list(get_dandiset_owners(dandiset).all()) == [user]

    # Verify that a draft Version and VersionMetadata were also created.
    assert dandiset.versions.count() == 1
    assert dandiset.most_recent_published_version is None
    assert dandiset.draft_version.version == 'draft'
    assert dandiset.draft_version.name == name
    assert dandiset.draft_version.status == Version.Status.PENDING

    # Verify that computed metadata was injected
    year = datetime.datetime.now(datetime.UTC).year
    url = f'{settings.DANDI_WEB_APP_URL}/dandiset/{dandiset.identifier}/draft'
    assert dandiset.draft_version.metadata == {
        **metadata,
        'manifestLocation': [
            f'{settings.DANDI_API_URL}/api/dandisets/{dandiset.identifier}/versions/draft/assets/'
        ],
        'name': name,
        'identifier': DANDISET_SCHEMA_ID_RE,
        'id': f'DANDI:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'citation': (
            f'{user.last_name}, {user.first_name} ({year}) {name} '
            f'(Version draft) [Data set]. DANDI Archive. {url}'
        ),
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',
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
def test_dandiset_rest_create_with_identifier(api_client):
    user = UserFactory.create(first_name='John', last_name='Doe', is_superuser=True)
    api_client.force_authenticate(user=user)
    name = 'Test Dandiset'
    identifier = '123456'
    metadata = {'foo': 'bar', 'identifier': f'DANDI:{identifier}'}

    response = api_client.post('/api/dandisets/', {'name': name, 'metadata': metadata})
    assert response.data == {
        'identifier': identifier,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'most_recent_published_version': None,
        'draft_version': {
            'version': 'draft',
            'name': name,
            'asset_count': 0,
            'active_uploads': 0,
            'size': 0,
            'status': 'Pending',
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'contact_person': 'Doe, John',
        'embargo_status': 'OPEN',
        'star_count': 0,
        'is_starred': False,
    }

    # Creating a Dandiset has side affects.
    # Verify that the user is the only owner.
    dandiset = Dandiset.objects.get(id=identifier)
    assert list(get_dandiset_owners(dandiset).all()) == [user]

    # Verify that a draft Version and VersionMetadata were also created.
    assert dandiset.versions.count() == 1
    assert dandiset.most_recent_published_version is None
    assert dandiset.draft_version.version == 'draft'
    assert dandiset.draft_version.name == name
    assert dandiset.draft_version.status == Version.Status.PENDING

    # Verify that computed metadata was injected
    year = datetime.datetime.now(datetime.UTC).year
    url = f'{settings.DANDI_WEB_APP_URL}/dandiset/{dandiset.identifier}/draft'
    assert dandiset.draft_version.metadata == {
        **metadata,
        'manifestLocation': [
            f'{settings.DANDI_API_URL}/api/dandisets/{dandiset.identifier}/versions/draft/assets/'
        ],
        'name': name,
        'identifier': f'DANDI:{identifier}',
        'id': f'DANDI:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'citation': (
            f'{user.last_name}, {user.first_name} ({year}) {name} '
            f'(Version draft) [Data set]. DANDI Archive. {url}'
        ),
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',
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
def test_dandiset_rest_create_with_contributor(api_client):
    user = UserFactory.create(first_name='John', last_name='Doe', is_superuser=True)
    api_client.force_authenticate(user=user)
    name = 'Test Dandiset'
    identifier = '123456'
    metadata = {
        'foo': 'bar',
        'identifier': f'DANDI:{identifier}',
        # This contributor is different from the user
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

    response = api_client.post('/api/dandisets/', {'name': name, 'metadata': metadata})
    assert response.data == {
        'identifier': identifier,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'most_recent_published_version': None,
        'draft_version': {
            'version': 'draft',
            'name': name,
            'asset_count': 0,
            'active_uploads': 0,
            'size': 0,
            'status': 'Pending',
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'contact_person': 'Jane Doe',
        'embargo_status': 'OPEN',
        'star_count': 0,
        'is_starred': False,
    }

    # Creating a Dandiset has side affects.
    # Verify that the user is the only owner.
    dandiset = Dandiset.objects.get(id=identifier)
    assert list(get_dandiset_owners(dandiset).all()) == [user]

    # Verify that a draft Version and VersionMetadata were also created.
    assert dandiset.versions.count() == 1
    assert dandiset.most_recent_published_version is None
    assert dandiset.draft_version.version == 'draft'
    assert dandiset.draft_version.name == name
    assert dandiset.draft_version.status == Version.Status.PENDING

    # Verify that computed metadata was injected
    year = datetime.datetime.now(datetime.UTC).year
    url = f'{settings.DANDI_WEB_APP_URL}/dandiset/{dandiset.identifier}/draft'
    assert dandiset.draft_version.metadata == {
        **metadata,
        'manifestLocation': [
            f'{settings.DANDI_API_URL}/api/dandisets/{dandiset.identifier}/versions/draft/assets/'
        ],
        'name': name,
        'identifier': f'DANDI:{identifier}',
        'id': f'DANDI:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'citation': (f'Jane Doe ({year}) {name} (Version draft) [Data set]. DANDI Archive. {url}'),
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',
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
def test_dandiset_rest_create_embargoed(api_client):
    user = UserFactory.create(first_name='John', last_name='Doe')
    api_client.force_authenticate(user=user)
    name = 'Test Dandiset'
    metadata = {'foo': 'bar'}

    response = api_client.post('/api/dandisets/?embargo=true', {'name': name, 'metadata': metadata})
    assert response.data == {
        'identifier': DANDISET_ID_RE,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'contact_person': 'Doe, John',
        'embargo_status': 'EMBARGOED',
        'star_count': 0,
        'is_starred': False,
        'draft_version': {
            'version': 'draft',
            'name': name,
            'asset_count': 0,
            'active_uploads': 0,
            'size': 0,
            'status': 'Pending',
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'most_recent_published_version': None,
    }
    dandiset_id = int(response.data['identifier'])

    # Creating a Dandiset has side affects.
    # Verify that the user is the only owner.
    dandiset = Dandiset.objects.get(id=dandiset_id)
    assert list(get_dandiset_owners(dandiset).all()) == [user]

    # Verify that a draft Version and VersionMetadata were also created.
    assert dandiset.versions.count() == 1
    assert dandiset.most_recent_published_version is None
    assert dandiset.draft_version.version == 'draft'
    assert dandiset.draft_version.name == name
    assert dandiset.draft_version.status == Version.Status.PENDING

    # Verify that computed metadata was injected
    year = datetime.datetime.now(datetime.UTC).year
    url = f'{settings.DANDI_WEB_APP_URL}/dandiset/{dandiset.identifier}/draft'
    assert dandiset.draft_version.metadata == {
        **metadata,
        'manifestLocation': [
            f'{settings.DANDI_API_URL}/api/dandisets/{dandiset.identifier}/versions/draft/assets/'
        ],
        'name': name,
        'identifier': DANDISET_SCHEMA_ID_RE,
        'id': f'DANDI:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'citation': (
            f'{user.last_name}, {user.first_name} ({year}) {name} '
            f'(Version draft) [Data set]. DANDI Archive. {url}'
        ),
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{settings.DANDI_SCHEMA_VERSION}/context.json',
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'schemaKey': 'Dandiset',
        'access': [
            {
                'schemaKey': 'AccessRequirements',
                'status': 'dandi:EmbargoedAccess',
                'embargoedUntil': DATE_RE,
            }
        ],
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
def test_dandiset_rest_create_embargoed_with_award_info(api_client: APIClient):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    name = 'Test Embargoed Dandiset'
    metadata = {'name': name, 'description': 'Test embargoed dandiset', 'license': ['spdx:CC0-1.0']}

    # Create embargoed dandiset with funding and award info
    embargo_end_date = (timezone.now().date() + datetime.timedelta(days=365)).isoformat()
    query_params = {
        'embargo': 'true',
        'funding_source': 'National Institutes of Health (NIH)',
        'award_number': 'R01MH123456',
        'embargo_end_date': embargo_end_date,
    }
    url = f'/api/dandisets/?{urlencode(query_params)}'

    response = api_client.post(url, {'name': name, 'metadata': metadata})

    assert response.status_code == 200
    assert response.data['embargo_status'] == 'EMBARGOED'

    # Verify the created dandiset in database
    dandiset = Dandiset.objects.get(id=response.data['identifier'])
    assert dandiset.embargo_status == Dandiset.EmbargoStatus.EMBARGOED

    # Check draft version metadata has access requirements
    assert dandiset.draft_version.metadata['access'] == [
        {
            'schemaKey': 'AccessRequirements',
            'status': 'dandi:EmbargoedAccess',
            'embargoedUntil': embargo_end_date,
        }
    ]

    # Check funding organization is added as contributor
    assert dandiset.draft_version.metadata['contributor'] == [
        {
            'schemaKey': 'Organization',
            'name': 'National Institutes of Health (NIH)',
            'awardNumber': 'R01MH123456',
            'roleName': ['dcite:Funder'],
            'includeInCitation': False,
        }
    ]


@pytest.mark.django_db
def test_dandiset_rest_create_embargoed_no_funding_info(api_client: APIClient):
    """Test creating embargoed dandiset with no funding source or award number (should succeed)."""
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    name = 'Test Embargoed Dandiset - No Funding'
    metadata = {'name': name, 'description': 'Test embargoed dandiset', 'license': ['spdx:CC0-1.0']}

    # Create embargoed dandiset without funding info
    query_params = {'embargo': 'true'}
    url = f'/api/dandisets/?{urlencode(query_params)}'

    response = api_client.post(url, {'name': name, 'metadata': metadata})

    assert response.status_code == 200
    assert response.data['embargo_status'] == 'EMBARGOED'

    # Verify the created dandiset in database
    dandiset = Dandiset.objects.get(id=response.data['identifier'])
    assert dandiset.embargo_status == Dandiset.EmbargoStatus.EMBARGOED

    # Check draft version metadata has access requirements with automatic 2-year embargo
    assert dandiset.draft_version.metadata['access'] == [
        {
            'schemaKey': 'AccessRequirements',
            'status': 'dandi:EmbargoedAccess',
            'embargoedUntil': DATE_RE,
        }
    ]

    # Verify embargo end date is approximately 2 years from now
    embargo_end_str = dandiset.draft_version.metadata['access'][0]['embargoedUntil']
    embargo_end = datetime.datetime.fromisoformat(embargo_end_str).date()
    expected_end = timezone.now().date() + datetime.timedelta(days=2 * 365)
    # Allow for some variance due to test execution time
    assert abs((embargo_end - expected_end).days) <= 1

    # Check that no funding organization is added as contributor
    assert [
        c
        for c in dandiset.draft_version.metadata['contributor']
        if c['schemaKey'] == 'Organization'
    ] == []


@pytest.mark.django_db
def test_dandiset_rest_create_embargoed_funding_no_award(api_client: APIClient):
    """Test creating embargoed dandiset with funding source but no award number (should fail)."""
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    name = 'Test Embargoed Dandiset - Funding Only'
    metadata = {'name': name, 'description': 'Test embargoed dandiset', 'license': ['spdx:CC0-1.0']}

    # Create embargoed dandiset with funding source but no award number
    query_params = {
        'embargo': 'true',
        'funding_source': 'National Institutes of Health (NIH)',
    }
    url = f'/api/dandisets/?{urlencode(query_params)}'

    response = api_client.post(url, {'name': name, 'metadata': metadata})

    assert response.status_code == 400


@pytest.mark.django_db
def test_dandiset_rest_create_embargoed_award_no_funding(api_client: APIClient):
    """Test creating embargoed dandiset with award number but no funding source (should fail)."""
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    name = 'Test Embargoed Dandiset - Award Only'
    metadata = {'name': name, 'description': 'Test embargoed dandiset', 'license': ['spdx:CC0-1.0']}

    # Create embargoed dandiset with award number but no funding source
    query_params = {
        'embargo': 'true',
        'award_number': 'R01MH123456',
    }
    url = f'/api/dandisets/?{urlencode(query_params)}'

    response = api_client.post(url, {'name': name, 'metadata': metadata})

    assert response.status_code == 400


@pytest.mark.django_db
def test_dandiset_rest_create_with_duplicate_identifier(api_client):
    user = UserFactory.create(is_superuser=True)
    dandiset = DandisetFactory.create()
    api_client.force_authenticate(user=user)
    name = 'Test Dandiset'
    identifier = dandiset.identifier
    metadata = {'foo': 'bar', 'identifier': f'DANDI:{identifier}'}

    response = api_client.post('/api/dandisets/', {'name': name, 'metadata': metadata})
    assert response.status_code == 400
    assert response.data == f'Dandiset {identifier} already exists'


@pytest.mark.django_db
def test_dandiset_rest_create_with_invalid_identifier(api_client):
    user = UserFactory.create(is_superuser=True)
    api_client.force_authenticate(user=user)
    name = 'Test Dandiset'
    identifier = 'abc123'
    metadata = {'foo': 'bar', 'identifier': identifier}

    response = api_client.post('/api/dandisets/', {'name': name, 'metadata': metadata})
    assert response.status_code == 400
    assert response.data == f'Invalid Identifier {identifier}'


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('embargo_status', 'success'),
    [
        (Dandiset.EmbargoStatus.OPEN, True),
        (Dandiset.EmbargoStatus.EMBARGOED, True),
        (Dandiset.EmbargoStatus.UNEMBARGOING, False),
    ],
)
def test_dandiset_rest_delete(api_client, draft_version_factory, embargo_status, success):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    # Ensure that open or embargoed dandisets can be deleted
    draft_version = draft_version_factory(
        dandiset__embargo_status=embargo_status, dandiset__owners=[user]
    )
    response = api_client.delete(f'/api/dandisets/{draft_version.dandiset.identifier}/')

    if success:
        assert response.status_code == 204
        assert not Dandiset.objects.all()
    else:
        assert response.status_code >= 400
        assert Dandiset.objects.count() == 1


@pytest.mark.django_db
def test_dandiset_rest_delete_with_zarrs(
    api_client,
    draft_version_factory,
    zarr_archive_factory,
    draft_asset_factory,
):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    draft_version = draft_version_factory(dandiset__owners=[user])
    zarr = zarr_archive_factory(dandiset=draft_version.dandiset)
    asset = draft_asset_factory(blob=None, zarr=zarr)

    # Add paths
    add_asset_paths(asset=asset, version=draft_version)

    # Delete
    response = api_client.delete(f'/api/dandisets/{draft_version.dandiset.identifier}/')
    assert response.status_code == 204
    assert not Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_delete_not_an_owner(api_client, draft_version):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    response = api_client.delete(f'/api/dandisets/{draft_version.dandiset.identifier}/')
    assert response.status_code == 403

    assert draft_version.dandiset in Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_delete_published(api_client, published_version_factory):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    published_version = published_version_factory(dandiset__owners=[user])

    response = api_client.delete(f'/api/dandisets/{published_version.dandiset.identifier}/')
    assert response.status_code == 403
    assert response.data == 'Cannot delete dandisets with published versions.'

    assert published_version.dandiset in Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_delete_published_admin(api_client, published_version):
    user = UserFactory.create(is_superuser=True)
    api_client.force_authenticate(user=user)

    response = api_client.delete(f'/api/dandisets/{published_version.dandiset.identifier}/')
    assert response.status_code == 403
    assert response.data == 'Cannot delete dandisets with published versions.'

    assert published_version.dandiset in Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_get_owners(api_client):
    user = UserFactory.create()
    dandiset = DandisetFactory.create(owners=[user])

    resp = api_client.get(f'/api/dandisets/{dandiset.identifier}/users/')

    assert resp.status_code == 200
    assert resp.data == [
        {
            'username': user.socialaccount_set.get().extra_data['login'],
            'name': user.socialaccount_set.get().extra_data['name'],
            'email': None,
        }
    ]


@pytest.mark.parametrize(
    'embargo_status',
    [Dandiset.EmbargoStatus.OPEN, Dandiset.EmbargoStatus.EMBARGOED],
)
@pytest.mark.django_db
def test_dandiset_rest_change_owner(
    api_client,
    draft_version_factory,
    mailoutbox,
    embargo_status,
):
    user1 = UserFactory.create()
    draft_version = draft_version_factory(
        dandiset__embargo_status=embargo_status, dandiset__owners=[user1]
    )
    dandiset = draft_version.dandiset
    api_client.force_authenticate(user=user1)

    user2 = UserFactory.create()
    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': user2.socialaccount_set.get().extra_data['login']}],
    )

    assert resp.status_code == 200
    assert resp.data == [
        {
            'username': user2.socialaccount_set.get().extra_data['login'],
            'name': user2.socialaccount_set.get().extra_data['name'],
            'email': user2.socialaccount_set.get().extra_data['email'],
        }
    ]
    assert list(get_dandiset_owners(dandiset)) == [user2]

    assert len(mailoutbox) == 2
    assert mailoutbox[0].subject == f'Removed from Dandiset "{dandiset.draft_version.name}"'
    assert mailoutbox[0].to == [user1.email]
    assert mailoutbox[1].subject == f'Added to Dandiset "{dandiset.draft_version.name}"'
    assert mailoutbox[1].to == [user2.email]


@pytest.mark.django_db
def test_dandiset_rest_change_owners_unembargo_in_progress(
    api_client,
    draft_version_factory,
):
    """Test that a dandiset undergoing unembargo prevents user modification."""
    user1 = UserFactory.create()
    draft_version = draft_version_factory(
        dandiset__embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING, dandiset__owners=[user1]
    )
    api_client.force_authenticate(user=user1)

    user2 = UserFactory.create()
    resp = api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/users/',
        [
            {'username': user1.socialaccount_set.get().extra_data['login']},
            {'username': user2.socialaccount_set.get().extra_data['login']},
        ],
    )

    assert resp.status_code == 400


@pytest.mark.django_db
def test_dandiset_rest_add_owner(
    api_client,
    draft_version_factory,
    mailoutbox,
):
    user1 = UserFactory.create()
    draft_version = draft_version_factory(dandiset__owners=[user1])
    dandiset = draft_version.dandiset
    api_client.force_authenticate(user=user1)

    user2 = UserFactory.create()
    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [
            {'username': user1.socialaccount_set.get().extra_data['login']},
            {'username': user2.socialaccount_set.get().extra_data['login']},
        ],
    )

    assert resp.status_code == 200
    assert resp.data == [
        {
            'username': user1.socialaccount_set.get().extra_data['login'],
            'name': user1.socialaccount_set.get().extra_data['name'],
            'email': user1.socialaccount_set.get().extra_data['email'],
        },
        {
            'username': user2.socialaccount_set.get().extra_data['login'],
            'name': user2.socialaccount_set.get().extra_data['name'],
            'email': user2.socialaccount_set.get().extra_data['email'],
        },
    ]
    assert list(get_dandiset_owners(dandiset)) == [user1, user2]

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == f'Added to Dandiset "{dandiset.draft_version.name}"'
    assert mailoutbox[0].to == [user2.email]


@pytest.mark.django_db
def test_dandiset_rest_add_owner_not_allowed(api_client, draft_version):
    user1 = UserFactory.create()
    user2 = UserFactory.create()
    api_client.force_authenticate(user=user1)

    resp = api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/users/',
        [
            {'username': user1.socialaccount_set.get().extra_data['login']},
            {'username': user2.socialaccount_set.get().extra_data['login']},
        ],
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dandiset_rest_remove_owner(
    api_client,
    draft_version_factory,
    mailoutbox,
):
    user1 = UserFactory.create()
    user2 = UserFactory.create()
    draft_version = draft_version_factory(dandiset__owners=[user1, user2])
    dandiset = draft_version.dandiset
    api_client.force_authenticate(user=user1)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': user1.socialaccount_set.get().extra_data['login']}],
    )

    assert resp.status_code == 200
    assert resp.data == [
        {
            'username': user1.socialaccount_set.get().extra_data['login'],
            'name': user1.socialaccount_set.get().extra_data['name'],
            'email': user1.socialaccount_set.get().extra_data['email'],
        }
    ]
    assert list(get_dandiset_owners(dandiset)) == [user1]

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == f'Removed from Dandiset "{dandiset.draft_version.name}"'
    assert mailoutbox[0].to == [user2.email]


@pytest.mark.django_db
def test_dandiset_rest_not_an_owner(api_client):
    user = UserFactory.create()
    dandiset = DandisetFactory.create()
    api_client.force_authenticate(user=user)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': user.socialaccount_set.get().extra_data['login']}],
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dandiset_rest_delete_all_owners_fails(api_client):
    user = UserFactory.create()
    dandiset = DandisetFactory.create(owners=[user])
    api_client.force_authenticate(user=user)

    resp = api_client.put(f'/api/dandisets/{dandiset.identifier}/users/', [])
    assert resp.status_code == 400
    assert resp.data == ['Cannot remove all draft owners']


@pytest.mark.django_db
def test_dandiset_rest_add_owner_does_not_exist(api_client):
    user = UserFactory.create()
    dandiset = DandisetFactory.create(owners=[user])
    api_client.force_authenticate(user=user)
    fake_name = user.socialaccount_set.get().extra_data['login'] + 'butnotreally'

    resp = api_client.put(f'/api/dandisets/{dandiset.identifier}/users/', [{'username': fake_name}])
    assert resp.status_code == 400
    assert resp.data == [f'User {fake_name} not found']


@pytest.mark.django_db
def test_dandiset_rest_add_malformed(api_client):
    user = UserFactory.create()
    dandiset = DandisetFactory.create(owners=[user])
    api_client.force_authenticate(user=user)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'email': user.socialaccount_set.get().extra_data['email']}],
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


@pytest.mark.django_db
def test_dandiset_rest_search_accented_characters(api_client, draft_version_factory):
    draft_version = draft_version_factory()
    draft_version.metadata['contributor'][0]['name'] = 'Buzsáki, György'
    draft_version.save()

    assert (
        api_client.get('/api/dandisets/', {'search': 'György'}).data['results']
        == api_client.get('/api/dandisets/', {'search': 'Gyorgy'}).data['results']
    )
    assert (
        api_client.get('/api/dandisets/', {'search': 'Buzsáki'}).data['results']
        == api_client.get('/api/dandisets/', {'search': 'Buzsaki'}).data['results']
    )


@pytest.mark.django_db
def test_dandiset_rest_search_many_versions(
    api_client, draft_version_factory, published_version_factory, dandiset
):
    draft_version = draft_version_factory(dandiset=dandiset)
    draft_version.metadata['contributor'][0]['name'] = 'testname'
    draft_version.save()

    published_version = published_version_factory(dandiset=dandiset)
    published_version.metadata['contributor'][0]['name'] = 'testname'
    published_version.save()

    results = api_client.get('/api/dandisets/', {'search': 'testname'}).data['results']
    assert len(results) == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    'contributors',
    [None, 'string', 1, [], {}],
)
def test_dandiset_contact_person_malformed_contributors(api_client, draft_version, contributors):
    draft_version.metadata['contributor'] = contributors
    draft_version.save()

    results = api_client.get(
        f'/api/dandisets/{draft_version.dandiset.identifier}/',
    )

    assert results.data['contact_person'] == ''


@pytest.mark.django_db
@pytest.mark.parametrize('embargoed', [False, True])
def test_dandiset_rest_list_active_uploads_not_owner(api_client, embargoed):
    user = UserFactory.create()
    ds = DandisetFactory.create(
        embargo_status=Dandiset.EmbargoStatus.EMBARGOED
        if embargoed
        else Dandiset.EmbargoStatus.OPEN
    )

    # Test unauthenticated
    response = api_client.get(f'/api/dandisets/{ds.identifier}/uploads/')
    assert response.status_code == 401

    # Test unauthorized
    api_client.force_authenticate(user=user)
    response = api_client.get(f'/api/dandisets/{ds.identifier}/uploads/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_dandiset_rest_list_active_uploads(api_client, draft_version_factory, upload_factory):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    draft_version = draft_version_factory(dandiset__owners=[user])
    dandiset = draft_version.dandiset
    upload = upload_factory(dandiset=dandiset)

    response = api_client.get(f'/api/dandisets/{dandiset.identifier}/uploads/')
    assert response.status_code == 200
    data = response.json()
    assert data['count'] == 1
    assert len(data['results']) == 1
    assert data['results'][0]['upload_id'] == upload.upload_id


@pytest.mark.django_db
@pytest.mark.parametrize('embargoed', [False, True])
def test_dandiset_rest_clear_active_uploads_not_owner(api_client, upload_factory, embargoed):
    user = UserFactory.create()
    dandiset = DandisetFactory.create(
        embargo_status=Dandiset.EmbargoStatus.EMBARGOED
        if embargoed
        else Dandiset.EmbargoStatus.OPEN
    )

    upload_factory(dandiset=dandiset)

    # Test unauthenticated
    response = api_client.delete(f'/api/dandisets/{dandiset.identifier}/uploads/')
    assert response.status_code == 401

    # Test unauthorized
    api_client.force_authenticate(user=user)
    response = api_client.delete(f'/api/dandisets/{dandiset.identifier}/uploads/')
    assert response.status_code == 403

    assert dandiset.uploads.count() == 1


@pytest.mark.django_db
def test_dandiset_rest_clear_active_uploads(api_client, draft_version_factory, upload_factory):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    draft_version = draft_version_factory(dandiset__owners=[user])
    dandiset = draft_version.dandiset
    upload_factory(dandiset=dandiset)

    response = api_client.get(f'/api/dandisets/{dandiset.identifier}/uploads/').json()
    assert response['count'] == 1
    assert len(response['results']) == 1

    response = api_client.delete(f'/api/dandisets/{dandiset.identifier}/uploads/')
    assert response.status_code == 204

    assert dandiset.uploads.count() == 0
    response = api_client.get(f'/api/dandisets/{dandiset.identifier}/uploads/').json()
    assert response['count'] == 0
    assert len(response['results']) == 0


@pytest.mark.django_db
def test_dandiset_star(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    dandiset = DandisetFactory.create()

    response = api_client.post(f'/api/dandisets/{dandiset.identifier}/star/')
    assert response.status_code == 200
    assert response.data == {'count': 1}
    assert dandiset.stars.count() == 1
    assert dandiset.stars.first().user == user


@pytest.mark.django_db
def test_dandiset_unstar(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    dandiset = DandisetFactory.create(starred_by=[user])

    response = api_client.delete(f'/api/dandisets/{dandiset.identifier}/star/')
    assert response.status_code == 200
    assert response.data == {'count': 0}
    assert dandiset.stars.count() == 0


@pytest.mark.django_db
def test_dandiset_star_unauthenticated(api_client):
    dandiset = DandisetFactory.create()
    response = api_client.post(f'/api/dandisets/{dandiset.identifier}/star/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_dandiset_star_count(api_client):
    dandiset = DandisetFactory.create(
        starred_by=[
            UserFactory.create(),
            UserFactory.create(),
            UserFactory.create(),
        ]
    )

    response = api_client.get(f'/api/dandisets/{dandiset.identifier}/')
    assert response.data['star_count'] == 3


@pytest.mark.django_db
def test_dandiset_is_starred_unauthenticated(api_client):
    dandiset = DandisetFactory.create()

    response = api_client.get(f'/api/dandisets/{dandiset.identifier}/')
    assert response.data['is_starred'] is False


@pytest.mark.django_db
def test_dandiset_is_starred_authenticated_unstarred(api_client):
    user = UserFactory.create()
    dandiset = DandisetFactory.create()
    api_client.force_authenticate(user=user)

    response = api_client.get(f'/api/dandisets/{dandiset.identifier}/')
    assert response.data['is_starred'] is False


@pytest.mark.django_db
def test_dandiset_is_starred_authenticated_starred(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    dandiset = DandisetFactory.create(starred_by=[user])

    response = api_client.get(f'/api/dandisets/{dandiset.identifier}/')
    assert response.data['is_starred'] is True


@pytest.mark.django_db
def test_dandiset_list_starred(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    # Star 2 out of 3 dandisets
    dandisets = [
        DandisetFactory.create(starred_by=[user]),
        DandisetFactory.create(starred_by=[user]),
        DandisetFactory.create(),
    ]

    # List starred dandisets
    response = api_client.get('/api/dandisets/', {'starred': True})
    assert response.status_code == 200
    assert response.data['count'] == 2
    assert {d['identifier'] for d in response.data['results']} == {
        dandisets[0].identifier,
        dandisets[1].identifier,
    }


@pytest.mark.django_db
def test_dandiset_list_order_size(api_client, draft_version_factory, asset_factory):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    dandisets: list[Dandiset] = [draft_version_factory().dandiset for _ in range(3)]

    # Create root asset path for each dandiset in varying size
    for i, ds in enumerate(dandisets):
        asset = asset_factory(blob__size=100 * i)
        add_asset_paths(asset=asset, version=ds.draft_version)

    # List dandisets by size
    response = api_client.get('/api/dandisets/', {'ordering': 'size'})
    assert response.status_code == 200
    assert response.data['count'] == len(dandisets)
    assert [d['identifier'] for d in response.data['results']] == [
        ds.identifier for ds in dandisets
    ]

    # List dandisets by reverse size
    response = api_client.get('/api/dandisets/', {'ordering': '-size'})
    assert response.status_code == 200
    assert response.data['count'] == len(dandisets)
    assert [d['identifier'] for d in response.data['results']] == [
        ds.identifier for ds in reversed(dandisets)
    ]


@pytest.mark.django_db
def test_dandiset_list_starred_unauthenticated(api_client):
    response = api_client.get('/api/dandisets/', {'starred': True})
    assert response.status_code == 401
