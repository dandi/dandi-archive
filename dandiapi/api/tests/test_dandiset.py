from __future__ import annotations

import datetime
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from dandischema.conf import get_instance_config
from dandischema.consts import DANDI_SCHEMA_VERSION
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.utils import timezone
import pytest

from dandiapi.api.asset_paths import add_asset_paths, add_version_asset_paths
from dandiapi.api.models import Dandiset, Version
from dandiapi.api.services.permissions.dandiset import (
    get_dandiset_owners,
    get_visible_dandisets,
)
from dandiapi.api.tests.factories import (
    DandisetFactory,
    DraftAssetFactory,
    DraftVersionFactory,
    PublishedVersionFactory,
    UserFactory,
)
from dandiapi.conftest import get_first_allowed_license

from .fuzzy import (
    DANDISET_ID_RE,
    DANDISET_SCHEMA_ID_RE,
    DATE_RE,
    TIMESTAMP_RE,
    UTC_ISO_TIMESTAMP_RE,
)

if TYPE_CHECKING:
    from rest_framework.test import APIClient


_SCHEMA_CONFIG = get_instance_config()


@pytest.mark.django_db
def test_dandiset_identifier():
    dandiset = DandisetFactory.create()
    assert int(dandiset.identifier) == dandiset.id


def test_dandiset_identifer_missing():
    dandiset = DandisetFactory.build()
    # This should have a sane fallback
    assert dandiset.identifier == ''


@pytest.mark.django_db
def test_dandiset_published_count():
    # empty dandiset
    DandisetFactory.create()
    # dandiset with draft version
    DraftVersionFactory.create(dandiset=DandisetFactory.create())
    # dandiset with published version
    PublishedVersionFactory.create(dandiset=DandisetFactory.create())

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
    asset_factory,
    params,
    results,
):
    # Create some dandisets of different kinds.
    #
    # Dandiset with empty draft
    empty_dandiset = DandisetFactory.create()
    DraftVersionFactory.create(dandiset=empty_dandiset)

    # Dandiset with populated draft
    draft_dandiset = DandisetFactory.create()
    draft_version = DraftVersionFactory.create(dandiset=draft_dandiset)
    draft_version.assets.add(asset_factory())
    add_version_asset_paths(draft_version)

    # Dandiset with published version
    published_dandiset = DandisetFactory.create()
    draft_version = DraftVersionFactory.create(dandiset=published_dandiset)
    draft_version.assets.add(asset_factory())
    add_version_asset_paths(draft_version)

    published_version = PublishedVersionFactory.create(dandiset=published_dandiset)
    published_version.assets.add(asset_factory())
    add_version_asset_paths(published_version)

    # Dandiset with published version and empty draft
    erased_dandiset = DandisetFactory.create()
    DraftVersionFactory.create(dandiset=erased_dandiset)
    published_version = PublishedVersionFactory.create(dandiset=erased_dandiset)
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
        'id': f'{_SCHEMA_CONFIG.instance_name}:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'citation': (
            f'{user.last_name}, {user.first_name} ({year}) {name} '
            f'(Version draft) [Data set]. DANDI Archive. {url}'
        ),
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{DANDI_SCHEMA_VERSION}/context.json',
        'schemaVersion': DANDI_SCHEMA_VERSION,
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
    metadata = {'foo': 'bar', 'identifier': f'{_SCHEMA_CONFIG.instance_name}:{identifier}'}

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
        'identifier': f'{_SCHEMA_CONFIG.instance_name}:{identifier}',
        'id': f'{_SCHEMA_CONFIG.instance_name}:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'citation': (
            f'{user.last_name}, {user.first_name} ({year}) {name} '
            f'(Version draft) [Data set]. DANDI Archive. {url}'
        ),
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{DANDI_SCHEMA_VERSION}/context.json',
        'schemaVersion': DANDI_SCHEMA_VERSION,
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
        'identifier': f'{_SCHEMA_CONFIG.instance_name}:{identifier}',
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
        'identifier': f'{_SCHEMA_CONFIG.instance_name}:{identifier}',
        'id': f'{_SCHEMA_CONFIG.instance_name}:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'citation': (f'Jane Doe ({year}) {name} (Version draft) [Data set]. DANDI Archive. {url}'),
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{DANDI_SCHEMA_VERSION}/context.json',
        'schemaVersion': DANDI_SCHEMA_VERSION,
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
        'id': f'{_SCHEMA_CONFIG.instance_name}:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'dateCreated': UTC_ISO_TIMESTAMP_RE,
        'citation': (
            f'{user.last_name}, {user.first_name} ({year}) {name} '
            f'(Version draft) [Data set]. DANDI Archive. {url}'
        ),
        '@context': f'https://raw.githubusercontent.com/dandi/schema/master/releases/{DANDI_SCHEMA_VERSION}/context.json',
        'schemaVersion': DANDI_SCHEMA_VERSION,
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
    metadata = {
        'name': name,
        'description': 'Test embargoed dandiset',
        'license': [get_first_allowed_license()],
    }

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
    assert dandiset.embargo_end_date == datetime.date.fromisoformat(embargo_end_date)

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
    metadata = {
        'name': name,
        'description': 'Test embargoed dandiset',
        'license': [get_first_allowed_license()],
    }

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
    metadata = {
        'name': name,
        'description': 'Test embargoed dandiset',
        'license': [get_first_allowed_license()],
    }

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
    metadata = {
        'name': name,
        'description': 'Test embargoed dandiset',
        'license': [get_first_allowed_license()],
    }

    # Create embargoed dandiset with award number but no funding source
    query_params = {
        'embargo': 'true',
        'award_number': 'R01MH123456',
    }
    url = f'/api/dandisets/?{urlencode(query_params)}'

    response = api_client.post(url, {'name': name, 'metadata': metadata})

    assert response.status_code == 400


@pytest.mark.django_db
def test_dandiset_rest_create_embargoed_embargo_end_date(api_client: APIClient):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    metadata = {
        'name': 'Test',
        'description': 'Test embargoed dandiset',
        'license': [get_first_allowed_license()],
    }

    # Keep embargo end date under two years from now, since no funding data was supplied
    end_date = timezone.now().date() + datetime.timedelta(days=485)
    query_params = urlencode({'embargo': 'true', 'embargo_end_date': end_date.isoformat()})
    response = api_client.post(
        f'/api/dandisets/?{query_params}',
        {'name': 'Test', 'metadata': metadata},
    )
    assert response.status_code == 200

    dandiset = Dandiset.objects.get(id=int(response.json()['identifier']))
    assert dandiset.embargo_end_date == end_date


@pytest.mark.django_db
def test_dandiset_rest_create_embargoed_embargo_end_date_default(api_client: APIClient):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        f'/api/dandisets/?{urlencode({"embargo": "true"})}',
        {
            'name': 'Test',
            'metadata': {
                'name': 'Test',
                'description': 'Test embargoed dandiset',
                'license': [get_first_allowed_license()],
            },
        },
    )
    assert response.status_code == 200

    dandiset = Dandiset.objects.get(id=response.data['identifier'])
    assert dandiset.embargo_end_date is not None
    expected_end = timezone.now().date() + datetime.timedelta(days=365 * 2)
    assert abs((dandiset.embargo_end_date - expected_end).days) <= 1


@pytest.mark.django_db
def test_dandiset_rest_create_with_duplicate_identifier(api_client):
    user = UserFactory.create(is_superuser=True)
    dandiset = DandisetFactory.create()
    api_client.force_authenticate(user=user)
    name = 'Test Dandiset'
    identifier = dandiset.identifier
    metadata = {'foo': 'bar', 'identifier': f'{_SCHEMA_CONFIG.instance_name}:{identifier}'}

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
def test_dandiset_rest_delete(api_client, embargo_status, success):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    # Ensure that open or embargoed dandisets can be deleted
    draft_version = DraftVersionFactory.create(
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
    zarr_archive_factory,
    draft_asset_factory,
):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    draft_version = DraftVersionFactory.create(dandiset__owners=[user])
    zarr = zarr_archive_factory(dandiset=draft_version.dandiset)
    asset = draft_asset_factory(blob=None, zarr=zarr)

    # Add paths
    add_asset_paths(asset=asset, version=draft_version)

    # Delete
    response = api_client.delete(f'/api/dandisets/{draft_version.dandiset.identifier}/')
    assert response.status_code == 204
    assert not Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_delete_not_an_owner(api_client):
    user = UserFactory.create()
    draft_version = DraftVersionFactory.create()
    api_client.force_authenticate(user=user)

    response = api_client.delete(f'/api/dandisets/{draft_version.dandiset.identifier}/')
    assert response.status_code == 403

    assert draft_version.dandiset in Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_delete_published(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    published_version = PublishedVersionFactory.create(dandiset__owners=[user])

    response = api_client.delete(f'/api/dandisets/{published_version.dandiset.identifier}/')
    assert response.status_code == 403
    assert response.data == 'Cannot delete dandisets with published versions.'

    assert published_version.dandiset in Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_delete_published_admin(api_client):
    user = UserFactory.create(is_superuser=True)
    published_version = PublishedVersionFactory.create()
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
    mailoutbox,
    embargo_status,
):
    user1 = UserFactory.create()
    draft_version = DraftVersionFactory.create(
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
):
    """Test that a dandiset undergoing unembargo prevents user modification."""
    user1 = UserFactory.create()
    draft_version = DraftVersionFactory.create(
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
    mailoutbox,
):
    user1 = UserFactory.create()
    draft_version = DraftVersionFactory.create(dandiset__owners=[user1])
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
def test_dandiset_rest_add_owner_not_allowed(api_client):
    user1 = UserFactory.create()
    user2 = UserFactory.create()
    draft_version = DraftVersionFactory.create()
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
    mailoutbox,
):
    user1 = UserFactory.create()
    user2 = UserFactory.create()
    draft_version = DraftVersionFactory.create(dandiset__owners=[user1, user2])
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
def test_dandiset_rest_search_identifier(api_client):
    draft_version = DraftVersionFactory.create()
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
def test_dandiset_rest_search_accented_characters(api_client):
    draft_version = DraftVersionFactory.create()
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
def test_dandiset_rest_search_many_versions(api_client):
    draft_version = DraftVersionFactory.create()
    draft_version.metadata['contributor'][0]['name'] = 'testname'
    draft_version.save()

    published_version = PublishedVersionFactory.create(dandiset=draft_version.dandiset)
    published_version.metadata['contributor'][0]['name'] = 'testname'
    published_version.save()

    results = api_client.get('/api/dandisets/', {'search': 'testname'}).data['results']
    assert len(results) == 1


@pytest.mark.django_db
def test_dandiset_rest_search_multiple_words_and_logic(api_client):
    """Test that search splits words and applies AND logic."""
    # Create a dandiset with specific metadata
    draft_version = DraftVersionFactory.create()
    draft_version.metadata['description'] = 'Study of neural activity in mouse cortex'
    draft_version.save()

    # Positive case: Both words present (in any order)
    # Search "neural mouse" should find the dandiset
    results = api_client.get('/api/dandisets/', {'search': 'neural mouse'}).data['results']
    assert len(results) == 1
    assert results[0]['identifier'] == draft_version.dandiset.identifier

    # Negative case: One word missing
    # Search "neural elephant" should NOT find the dandiset
    results = api_client.get('/api/dandisets/', {'search': 'neural elephant'}).data['results']
    assert len(results) == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    'contributors',
    [None, 'string', 1, [], {}],
)
def test_dandiset_contact_person_malformed_contributors(api_client, contributors):
    draft_version = DraftVersionFactory.create()
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
def test_dandiset_rest_list_active_uploads(api_client, upload_factory):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    draft_version = DraftVersionFactory.create(dandiset__owners=[user])
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
def test_dandiset_rest_clear_active_uploads(api_client, upload_factory):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    draft_version = DraftVersionFactory.create(dandiset__owners=[user])
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
def test_dandiset_list_order_size(api_client, asset_factory):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    dandisets: list[Dandiset] = [DraftVersionFactory.create().dandiset for _ in range(3)]

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


# --- Advanced (Gmail-style) search ---------------------------------------------------------------


def _refresh_asset_search():
    with connection.cursor() as cursor:
        cursor.execute('REFRESH MATERIALIZED VIEW asset_search;')


def _seed_dandiset_with_asset(*, asset_metadata: dict, embargoed: bool = False) -> Dandiset:
    """Create a draft dandiset + version + single asset with the given metadata.

    Caller is responsible for `_refresh_asset_search()` after seeding all
    fixtures so the materialized view sees them.
    """
    embargo_status = Dandiset.EmbargoStatus.EMBARGOED if embargoed else Dandiset.EmbargoStatus.OPEN
    dandiset = DandisetFactory.create(embargo_status=embargo_status)
    version = DraftVersionFactory.create(dandiset=dandiset)
    base_metadata = {
        'schemaVersion': DANDI_SCHEMA_VERSION,
        'schemaKey': 'Asset',
        'encodingFormat': 'application/x-nwb',
    }
    version.assets.add(DraftAssetFactory.create(metadata={**base_metadata, **asset_metadata}))
    add_version_asset_paths(version)
    return dandiset


def _search_ids(api_client, query: str) -> set[str]:
    response = api_client.get(
        '/api/dandisets/',
        {'draft': 'true', 'empty': 'true', 'search': query},
    )
    assert response.status_code == 200
    return {r['identifier'] for r in response.json()['results']}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_created_after_filters_dandisets(api_client):
    old = DandisetFactory.create()
    new = DandisetFactory.create()
    DraftVersionFactory.create(dandiset=old)
    DraftVersionFactory.create(dandiset=new)

    cutoff = timezone.now() - datetime.timedelta(days=1)
    Dandiset.objects.filter(pk=old.pk).update(created=cutoff - datetime.timedelta(days=30))

    after_str = (cutoff + datetime.timedelta(seconds=1)).date().isoformat()
    response = api_client.get(
        '/api/dandisets/',
        {'draft': 'true', 'empty': 'true', 'search': f'created_after:{after_str}'},
    )
    assert response.status_code == 200
    ids = {r['identifier'] for r in response.json()['results']}
    assert ids == {new.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_created_before_filters_dandisets(api_client):
    old = DandisetFactory.create()
    new = DandisetFactory.create()
    DraftVersionFactory.create(dandiset=old)
    DraftVersionFactory.create(dandiset=new)

    cutoff = timezone.now() - datetime.timedelta(days=1)
    Dandiset.objects.filter(pk=old.pk).update(created=cutoff - datetime.timedelta(days=30))

    before_str = cutoff.date().isoformat()
    response = api_client.get(
        '/api/dandisets/',
        {'draft': 'true', 'empty': 'true', 'search': f'created_before:{before_str}'},
    )
    assert response.status_code == 200
    ids = {r['identifier'] for r in response.json()['results']}
    assert ids == {old.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_species_matches(api_client):
    mouse_dandiset = DandisetFactory.create()
    rat_dandiset = DandisetFactory.create()
    mouse_version = DraftVersionFactory.create(dandiset=mouse_dandiset)
    rat_version = DraftVersionFactory.create(dandiset=rat_dandiset)

    mouse_asset = DraftAssetFactory.create(
        metadata={
            'schemaVersion': DANDI_SCHEMA_VERSION,
            'schemaKey': 'Asset',
            'encodingFormat': 'application/x-nwb',
            'wasAttributedTo': [{'species': {'name': 'House mouse'}}],
        },
    )
    rat_asset = DraftAssetFactory.create(
        metadata={
            'schemaVersion': DANDI_SCHEMA_VERSION,
            'schemaKey': 'Asset',
            'encodingFormat': 'application/x-nwb',
            'wasAttributedTo': [{'species': {'name': 'Norway rat'}}],
        },
    )
    mouse_version.assets.add(mouse_asset)
    rat_version.assets.add(rat_asset)
    add_version_asset_paths(mouse_version)
    add_version_asset_paths(rat_version)
    _refresh_asset_search()

    response = api_client.get(
        '/api/dandisets/',
        {'draft': 'true', 'empty': 'true', 'search': 'species:mouse'},
    )
    assert response.status_code == 200
    ids = {r['identifier'] for r in response.json()['results']}
    assert ids == {mouse_dandiset.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_unknown_operator_returns_400_with_suggestion(api_client):
    # Unknown operators raise SearchSyntaxError → DRF 400. Close-by operator
    # names get a "Did you mean?" hint via difflib.
    response = api_client.get(
        '/api/dandisets/',
        {'draft': 'true', 'empty': 'true', 'search': 'specie:mouse'},
    )
    assert response.status_code == 400
    assert 'species' in response.json()['search']


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_quoted_operator_like_token_is_free_text(api_client):
    # Wrapping an operator-like token in quotes opts out of operator parsing,
    # letting users search for a literal colon when needed.
    DandisetFactory.create()
    DraftVersionFactory.create()

    response = api_client.get(
        '/api/dandisets/',
        {'draft': 'true', 'empty': 'true', 'search': '"foo:bar_no_such_string_here"'},
    )
    assert response.status_code == 200
    assert response.json()['count'] == 0


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_combines_free_text_and_operator(api_client):
    # A dandiset whose metadata contains a unique token, plus a matching species.
    target = DandisetFactory.create()
    other = DandisetFactory.create()
    target_version = DraftVersionFactory.create(dandiset=target)
    other_version = DraftVersionFactory.create(dandiset=other)

    # Inject a unique token into the target version's metadata
    target_version.metadata = {**target_version.metadata, 'description': 'unique_search_marker_xyz'}
    target_version.save()

    species_metadata = {
        'schemaVersion': DANDI_SCHEMA_VERSION,
        'schemaKey': 'Asset',
        'encodingFormat': 'application/x-nwb',
        'wasAttributedTo': [{'species': {'name': 'House mouse'}}],
    }
    target_version.assets.add(DraftAssetFactory.create(metadata=species_metadata))
    other_version.assets.add(DraftAssetFactory.create(metadata=species_metadata))
    add_version_asset_paths(target_version)
    add_version_asset_paths(other_version)
    _refresh_asset_search()

    response = api_client.get(
        '/api/dandisets/',
        {
            'draft': 'true',
            'empty': 'true',
            'search': 'unique_search_marker_xyz species:mouse',
        },
    )
    assert response.status_code == 200
    ids = {r['identifier'] for r in response.json()['results']}
    assert ids == {target.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_modified_after_uses_latest_version(api_client):
    # The most-recent version (by created order) determines the "modified" timestamp.
    old = DandisetFactory.create()
    new = DandisetFactory.create()
    old_version = DraftVersionFactory.create(dandiset=old)
    new_version = DraftVersionFactory.create(dandiset=new)

    cutoff = timezone.now()
    Version.objects.filter(pk=old_version.pk).update(modified=cutoff - datetime.timedelta(days=30))
    Version.objects.filter(pk=new_version.pk).update(modified=cutoff + datetime.timedelta(days=1))

    after_str = (cutoff + datetime.timedelta(seconds=1)).date().isoformat()
    assert _search_ids(api_client, f'modified_after:{after_str}') == {new.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_published_filters_use_published_versions_only(api_client):
    # A draft-only dandiset is invisible to published_* operators, even if its
    # draft version's `created` falls in range.
    draft_only = DandisetFactory.create()
    DraftVersionFactory.create(dandiset=draft_only)

    published_ds = DandisetFactory.create()
    DraftVersionFactory.create(dandiset=published_ds)
    pub_version = PublishedVersionFactory.create(dandiset=published_ds)

    cutoff = timezone.now()
    Version.objects.filter(pk=pub_version.pk).update(created=cutoff - datetime.timedelta(days=30))

    before_str = cutoff.date().isoformat()
    # published_before should match only published_ds (the draft-only one is excluded
    # because it has no published version, so the annotation is NULL).
    assert _search_ids(api_client, f'published_before:{before_str}') == {published_ds.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_repeated_date_operators_combine(api_client):
    # modified_before AND modified_after applied together — exercises the
    # "annotated set" guard so we don't add the same annotation twice.
    too_old = DandisetFactory.create()
    in_range = DandisetFactory.create()
    too_new = DandisetFactory.create()

    for ds, modified_offset in [
        (too_old, datetime.timedelta(days=-30)),
        (in_range, datetime.timedelta(days=0)),
        (too_new, datetime.timedelta(days=30)),
    ]:
        version = DraftVersionFactory.create(dandiset=ds)
        Version.objects.filter(pk=version.pk).update(modified=timezone.now() + modified_offset)

    one_week_ago = (timezone.now() - datetime.timedelta(days=7)).date().isoformat()
    one_week_from_now = (timezone.now() + datetime.timedelta(days=7)).date().isoformat()
    query = f'modified_after:{one_week_ago} modified_before:{one_week_from_now}'
    assert _search_ids(api_client, query) == {in_range.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_malformed_date_returns_400(api_client):
    # A bad date in a date operator now raises so the user sees the typo.
    DandisetFactory.create()
    DraftVersionFactory.create()

    response = api_client.get(
        '/api/dandisets/',
        {'draft': 'true', 'empty': 'true', 'search': 'created_after:not-a-date'},
    )
    assert response.status_code == 400
    assert 'YYYY-MM-DD' in response.json()['search']


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_unbalanced_quote_returns_400(api_client):
    response = api_client.get(
        '/api/dandisets/',
        {'draft': 'true', 'empty': 'true', 'search': 'hello "world species:mouse'},
    )
    assert response.status_code == 400
    assert 'Unbalanced quote' in response.json()['search']


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_species_substring_match(api_client):
    # Real DANDI species are like "Mus musculus - House mouse". A short token
    # like "mouse" should match by case-insensitive substring against the
    # `wasAttributedTo[*].species.name` jsonpath.
    mouse = _seed_dandiset_with_asset(
        asset_metadata={'wasAttributedTo': [{'species': {'name': 'Mus musculus - House mouse'}}]},
    )
    rat = _seed_dandiset_with_asset(
        asset_metadata={
            'wasAttributedTo': [{'species': {'name': 'Rattus norvegicus - Norway rat'}}]
        },
    )
    _refresh_asset_search()

    assert _search_ids(api_client, 'species:mouse') == {mouse.identifier}
    assert _search_ids(api_client, 'species:musculus') == {mouse.identifier}
    assert _search_ids(api_client, 'species:Rattus') == {rat.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_species_matches_any_attributed_subject(api_client):
    # An asset can be attributed to multiple subjects of different species
    # (e.g. xenotransplantation, multi-species recordings). The filter must
    # scan every wasAttributedTo entry, not just the first.
    multi = _seed_dandiset_with_asset(
        asset_metadata={
            'wasAttributedTo': [
                {'species': {'name': 'House mouse'}},
                {'species': {'name': 'Human'}},
            ],
        },
    )
    rat = _seed_dandiset_with_asset(
        asset_metadata={'wasAttributedTo': [{'species': {'name': 'Norway rat'}}]},
    )
    _refresh_asset_search()

    # `multi` matches both queries because every array element is scanned.
    assert _search_ids(api_client, 'species:Human') == {multi.identifier}
    assert _search_ids(api_client, 'species:mouse') == {multi.identifier}
    assert _search_ids(api_client, 'species:rat') == {rat.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_approach_matches_any_array_element(api_client):
    # Real DANDI assets often have multiple approach entries (e.g. dandiset
    # 000017 lists both "electrophysiological approach" and "behavioral
    # approach"). The filter must match if ANY element's name matches —
    # not just the first.
    ephys_only = _seed_dandiset_with_asset(
        asset_metadata={'approach': [{'name': 'electrophysiological approach'}]},
    )
    behav_only = _seed_dandiset_with_asset(
        asset_metadata={'approach': [{'name': 'behavioral approach'}]},
    )
    multi = _seed_dandiset_with_asset(
        asset_metadata={
            'approach': [
                {'name': 'behavioral approach'},
                {'name': 'electrophysiological approach'},
            ],
        },
    )
    _refresh_asset_search()

    # `multi` matches both queries because every array element is scanned.
    assert _search_ids(api_client, 'approach:electrophysiological') == {
        ephys_only.identifier,
        multi.identifier,
    }
    assert _search_ids(api_client, 'approach:behavioral') == {
        behav_only.identifier,
        multi.identifier,
    }


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_approach_handles_regex_metacharacters(api_client):
    # Postgres jsonpath like_regex would otherwise interpret `[`, `*`, etc. as
    # regex metacharacters. The filter must escape them so a search for `[pilot]`
    # matches a literal `[pilot]` in the name.
    bracket = _seed_dandiset_with_asset(
        asset_metadata={'approach': [{'name': 'electrophysiological [pilot]'}]},
    )
    _refresh_asset_search()

    assert _search_ids(api_client, 'approach:[pilot]') == {bracket.identifier}
    # An unrelated metacharacter shouldn't match this name.
    assert _search_ids(api_client, 'approach:*') == set()


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_technique_with_quoted_phrase(api_client):
    # Quoted multi-word values must be parsed as a single token.
    spike = _seed_dandiset_with_asset(
        asset_metadata={'measurementTechnique': [{'name': 'spike sorting technique'}]},
    )
    surg = _seed_dandiset_with_asset(
        asset_metadata={'measurementTechnique': [{'name': 'surgical technique'}]},
    )
    _refresh_asset_search()

    assert _search_ids(api_client, 'technique:"spike sorting"') == {spike.identifier}
    assert _search_ids(api_client, 'technique:surgical') == {surg.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_standard_matches(api_client):
    nwb = _seed_dandiset_with_asset(
        asset_metadata={'dataStandard': [{'name': 'Neurodata Without Borders (NWB)'}]},
    )
    bids = _seed_dandiset_with_asset(
        asset_metadata={'dataStandard': [{'name': 'Brain Imaging Data Structure (BIDS)'}]},
    )
    _refresh_asset_search()

    assert _search_ids(api_client, 'standard:NWB') == {nwb.identifier}
    assert _search_ids(api_client, 'standard:BIDS') == {bids.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_file_type_alias_and_mime(api_client):
    nwb = _seed_dandiset_with_asset(asset_metadata={'encodingFormat': 'application/x-nwb'})
    image = _seed_dandiset_with_asset(asset_metadata={'encodingFormat': 'image/tiff'})
    text = _seed_dandiset_with_asset(asset_metadata={'encodingFormat': 'text/plain'})
    _refresh_asset_search()

    # The short alias `nwb` resolves to the application/x-nwb mime prefix.
    assert _search_ids(api_client, 'file_type:nwb') == {nwb.identifier}
    # The `image` alias matches anything starting with `image/`.
    assert _search_ids(api_client, 'file_type:image') == {image.identifier}
    assert _search_ids(api_client, 'file_type:text') == {text.identifier}
    # Direct MIME prefixes also work.
    assert _search_ids(api_client, 'file_type:application/x-nwb') == {nwb.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_repeated_asset_operators_intersect(api_client):
    # Cross-key semantics: a SINGLE asset must satisfy ALL constraints. So
    # `species:mouse approach:electrophysiological` requires one asset that
    # is both attributed to a mouse AND uses an electrophysiological approach.
    # An asset that has the species but a different approach (and vice versa
    # for a sibling dandiset) does NOT qualify.
    mouse_ephys = _seed_dandiset_with_asset(
        asset_metadata={
            'wasAttributedTo': [{'species': {'name': 'House mouse'}}],
            'approach': [{'name': 'electrophysiological approach'}],
        },
    )
    _seed_dandiset_with_asset(
        asset_metadata={
            'wasAttributedTo': [{'species': {'name': 'House mouse'}}],
            'approach': [{'name': 'behavioral approach'}],
        },
    )
    _seed_dandiset_with_asset(
        asset_metadata={
            'wasAttributedTo': [{'species': {'name': 'Norway rat'}}],
            'approach': [{'name': 'electrophysiological approach'}],
        },
    )
    _refresh_asset_search()

    query = 'species:mouse approach:electrophysiological'
    assert _search_ids(api_client, query) == {mouse_ephys.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_repeated_same_key_operator_combines_with_and(api_client):
    # Same-key semantics: `species:mouse species:rat` requires a single
    # asset whose species set contains BOTH "mouse" and "rat" (matches
    # GitHub's default for repeated keys). Pinning this so a future change
    # to OR-within-key is a deliberate decision, not a regression.
    multi = _seed_dandiset_with_asset(
        asset_metadata={
            'wasAttributedTo': [
                {'species': {'name': 'House mouse'}},
                {'species': {'name': 'Norway rat'}},
            ],
        },
    )
    _seed_dandiset_with_asset(
        asset_metadata={'wasAttributedTo': [{'species': {'name': 'House mouse'}}]},
    )
    _seed_dandiset_with_asset(
        asset_metadata={'wasAttributedTo': [{'species': {'name': 'Norway rat'}}]},
    )
    _refresh_asset_search()

    assert _search_ids(api_client, 'species:mouse species:rat') == {multi.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_empty_operator_value_returns_400(api_client):
    response = api_client.get(
        '/api/dandisets/',
        # Trailing space → empty value after strip()
        {'draft': 'true', 'empty': 'true', 'search': 'species:" "'},
    )
    assert response.status_code == 400
    assert 'requires a value' in response.json()['search']


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_species_respects_embargo_visibility(api_client):
    # An anonymous user must not be able to surface embargoed dandisets via has_*.
    open_ds = _seed_dandiset_with_asset(
        asset_metadata={'wasAttributedTo': [{'species': {'name': 'House mouse'}}]},
    )
    _seed_dandiset_with_asset(
        asset_metadata={'wasAttributedTo': [{'species': {'name': 'House mouse'}}]},
        embargoed=True,
    )
    _refresh_asset_search()

    # Anonymous request: embargoed must be filtered out.
    assert _search_ids(api_client, 'species:mouse') == {open_ds.identifier}


# --- owner: operator -----------------------------------------------------------------------------


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_owner_lookup_paths_and_combinations(api_client):
    """One setup, many assertions for the owner: operator.

    Resolves users by every documented lookup path, unions across multiple
    matched users, returns 0 for unknown values, is case-insensitive, and
    combines correctly with other operators (cross-key AND on the same
    dandiset).
    """
    # Three users with overlapping last names so we can exercise every lookup
    # path AND the multi-user union in a single setup.
    alice = UserFactory.create(
        username='Alice', email='Alice@Example.com', first_name='Alice', last_name='Smith'
    )
    bob = UserFactory.create(
        username='bob', email='bob@example.com', first_name='Bob', last_name='Smith'
    )
    carol = UserFactory.create(
        username='carol', email='carol@example.com', first_name='Carol', last_name='Jones'
    )
    alice_old = DandisetFactory.create(owners=[alice])
    alice_new = DandisetFactory.create(owners=[alice])
    bob_ds = DandisetFactory.create(owners=[bob])
    carol_ds = DandisetFactory.create(owners=[carol])
    for ds in (alice_old, alice_new, bob_ds, carol_ds):
        DraftVersionFactory.create(dandiset=ds)

    # Backdate alice_old so we can intersect with a date operator below.
    cutoff = timezone.now() - datetime.timedelta(days=1)
    Dandiset.objects.filter(pk=alice_old.pk).update(created=cutoff - datetime.timedelta(days=30))
    after_str = (cutoff + datetime.timedelta(seconds=1)).date().isoformat()

    alice_dsets = {alice_old.identifier, alice_new.identifier}

    # username (case-insensitive)
    assert _search_ids(api_client, 'owner:alice') == alice_dsets
    assert _search_ids(api_client, 'owner:ALICE') == alice_dsets

    # email (case-insensitive)
    assert _search_ids(api_client, 'owner:alice@example.com') == alice_dsets
    assert _search_ids(api_client, 'owner:ALICE@Example.com') == alice_dsets

    # first / last / full name
    assert _search_ids(api_client, 'owner:Bob') == {bob_ds.identifier}
    assert _search_ids(api_client, 'owner:Jones') == {carol_ds.identifier}
    assert _search_ids(api_client, 'owner:"Carol Jones"') == {carol_ds.identifier}

    # union: shared last name returns dandisets from both users
    assert _search_ids(api_client, 'owner:Smith') == alice_dsets | {bob_ds.identifier}

    # unknown user → 0 results, not 400 (a valid 0-hit query)
    assert _search_ids(api_client, 'owner:no_such_user_anywhere') == set()

    # combines with other operators: cross-key AND on the same dandiset.
    # Only alice_new satisfies BOTH owner:alice AND created_after.
    assert _search_ids(api_client, f'owner:alice created_after:{after_str}') == {
        alice_new.identifier
    }


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_owner_does_not_inflate_to_superuser_archive(api_client):
    # Guardian's get_objects_for_user(with_superuser=True) returns ALL objects
    # for superusers — wrong semantics for owner: searches. We pass
    # with_superuser=False so `owner:admin` returns only what admin
    # explicitly owns, not the entire archive.
    admin = UserFactory.create(username='admin', is_superuser=True)
    other = UserFactory.create()
    DraftVersionFactory.create(dandiset=DandisetFactory.create(owners=[other]))
    admin_owned = DandisetFactory.create(owners=[admin])
    DraftVersionFactory.create(dandiset=admin_owned)

    assert _search_ids(api_client, 'owner:admin') == {admin_owned.identifier}


# --- contributor / role operators ----------------------------------------------------------------


def _seed_dandiset_with_contributors(*, contributors: list[dict]) -> Dandiset:
    """Create a draft dandiset with the given contributor list on its version.

    Used by the contributor/role tests below.
    """
    dandiset = DandisetFactory.create()
    version = DraftVersionFactory.create(dandiset=dandiset)
    version.metadata = {**version.metadata, 'contributor': contributors}
    version.save()
    return dandiset


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_contributor_and_role_operators(api_client):
    """One setup, many assertions for the contributor + role operators.

    Covers the catch-all `contributor:`, several role-specific operators
    (author/data_curator/funder/contact_person), independent-operator AND
    semantics across roles, name vs email lookup, case-insensitive substring,
    role substring (`data_curator:` matches `dcite:DataCurator`), and the
    "different elements may satisfy different operators" composability that
    distinguishes Option D from same-element semantics.
    """
    # Three dandisets with overlapping names but different role assignments.
    # Realistic identifiers: ORCID for Persons, ROR URL for Organizations.
    ds_doe_curator = _seed_dandiset_with_contributors(
        contributors=[
            {
                'name': 'Doe, Jane',
                'email': 'jane.doe@example.com',
                'identifier': '0000-0002-2990-9889',
                'roleName': ['dcite:DataCurator', 'dcite:Author'],
                'schemaKey': 'Person',
            },
            {
                'name': 'National Institutes of Health',
                'identifier': 'https://ror.org/01cwqze88',
                'roleName': ['dcite:Funder'],
                'schemaKey': 'Organization',
            },
        ],
    )
    ds_doe_author_only = _seed_dandiset_with_contributors(
        contributors=[
            {
                'name': 'Doe, Jane',
                'identifier': '0000-0001-2222-3333',
                'roleName': ['dcite:Author'],
                'schemaKey': 'Person',
            },
        ],
    )
    ds_smith_curator = _seed_dandiset_with_contributors(
        contributors=[
            {
                'name': 'Smith, Alice',
                'roleName': ['dcite:DataCurator'],
                'schemaKey': 'Person',
            },
        ],
    )

    # `contributor:` (catch-all) — any role
    assert _search_ids(api_client, 'contributor:Doe') == {
        ds_doe_curator.identifier,
        ds_doe_author_only.identifier,
    }
    assert _search_ids(api_client, 'contributor:NIH') == set()  # full org name only
    assert _search_ids(api_client, 'contributor:"National Institutes"') == {
        ds_doe_curator.identifier
    }
    # Email lookup also works via the catch-all.
    assert _search_ids(api_client, 'contributor:jane.doe@example.com') == {
        ds_doe_curator.identifier
    }

    # role-specific: author:Doe matches the two dandisets where Doe has Author role
    assert _search_ids(api_client, 'author:Doe') == {
        ds_doe_curator.identifier,
        ds_doe_author_only.identifier,
    }
    # data_curator:Doe matches only the dandiset where Doe is also a curator
    assert _search_ids(api_client, 'data_curator:Doe') == {ds_doe_curator.identifier}
    # data_curator:Smith matches the smith dandiset
    assert _search_ids(api_client, 'data_curator:Smith') == {ds_smith_curator.identifier}
    # funder:"National Institutes" only the one with NIH funder
    assert _search_ids(api_client, 'funder:"National Institutes"') == {ds_doe_curator.identifier}

    # Case-insensitive on both name and role
    assert _search_ids(api_client, 'AUTHOR:doe') == {
        ds_doe_curator.identifier,
        ds_doe_author_only.identifier,
    }

    # Identifier lookup: full ORCID for Person, full ROR URL for Org, AND
    # bare-id substring forms (`01cwqze88` matches the ROR URL via icontains).
    assert _search_ids(api_client, 'contributor:0000-0002-2990-9889') == {ds_doe_curator.identifier}
    assert _search_ids(api_client, 'contributor:"https://ror.org/01cwqze88"') == {
        ds_doe_curator.identifier
    }
    assert _search_ids(api_client, 'contributor:01cwqze88') == {ds_doe_curator.identifier}
    # Identifier lookup composes with role: a role-specific operator with an
    # ORCID also requires the matched contributor to hold that role.
    assert _search_ids(api_client, 'data_curator:0000-0002-2990-9889') == {
        ds_doe_curator.identifier
    }
    # Wrong role for that ORCID → 0 (Doe @ ds_doe_curator IS a curator,
    # but Doe @ ds_doe_author_only has a different ORCID).
    assert _search_ids(api_client, 'data_curator:0000-0001-2222-3333') == set()

    # Independent-operator AND across DIFFERENT contributor elements:
    # `author:Doe funder:"National Institutes"` matches the dandiset where
    # one contributor element is Doe-as-Author AND a different contributor
    # element is NIH-as-Funder. (This is the Option D semantic the user
    # specifically wanted — with same-element semantics the query would
    # require Doe to himself be a Funder, which is wrong.)
    assert _search_ids(api_client, 'author:Doe funder:"National Institutes"') == {
        ds_doe_curator.identifier
    }


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_contributor_role_substring_match(api_client):
    """Role substring matches the dcite:-prefixed stored value.

    `data_curator:` should match the stored value `dcite:DataCurator` via
    case-insensitive substring on `roleName` — users don't have to type
    the `dcite:` prefix.
    """
    ds = _seed_dandiset_with_contributors(
        contributors=[
            {
                'name': 'Curator, Connie',
                'roleName': ['dcite:DataCurator'],  # stored with dcite: prefix
                'schemaKey': 'Person',
            },
        ],
    )

    # The operator name maps to the substring "DataCurator" (without the
    # "dcite:" prefix) and matches the stored "dcite:DataCurator" via
    # case-insensitive regex inside the jsonpath.
    assert _search_ids(api_client, 'data_curator:Curator') == {ds.identifier}


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_unknown_role_operator_returns_400_with_suggestion(api_client):
    response = api_client.get(
        '/api/dandisets/',
        {'draft': 'true', 'empty': 'true', 'search': 'data_curatr:Doe'},
    )
    assert response.status_code == 400
    assert 'data_curator' in response.json()['search']


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_advanced_search_affiliation_operator(api_client):
    """`affiliation:` queries the nested Person.affiliation[] field, not roleName.

    Real DANDI data stores affiliations on the Person object itself (e.g.
    `Doe, Jane` is affiliated with Stanford via `Doe.affiliation[0].name`),
    not as a `dcite:Affiliation` roleName entry. Match by org name OR by
    the affiliation's ROR identifier; substring forms work for both.
    """
    ds_stanford = _seed_dandiset_with_contributors(
        contributors=[
            {
                'name': 'Doe, Jane',
                'roleName': ['dcite:Author'],
                'schemaKey': 'Person',
                'affiliation': [
                    {
                        'name': 'Stanford University',
                        'identifier': 'https://ror.org/00f54p054',
                        'schemaKey': 'Affiliation',
                    },
                ],
            },
        ],
    )
    ds_ucl = _seed_dandiset_with_contributors(
        contributors=[
            {
                'name': 'Doe, Jane',
                'roleName': ['dcite:Author'],
                'schemaKey': 'Person',
                'affiliation': [
                    {
                        'name': 'University College London',
                        'schemaKey': 'Affiliation',
                    },
                ],
            },
        ],
    )

    # Affiliation by organization name
    assert _search_ids(api_client, 'affiliation:Stanford') == {ds_stanford.identifier}
    assert _search_ids(api_client, 'affiliation:"University College London"') == {ds_ucl.identifier}
    # Affiliation by ROR identifier (full URL or bare ID via substring)
    assert _search_ids(api_client, 'affiliation:00f54p054') == {ds_stanford.identifier}

    # Composes with role/contributor operators on the same Version (different
    # contributor elements OK — but here both must match Doe, who is the only
    # contributor in each fixture, so the joint constraint is just an AND).
    assert _search_ids(api_client, 'author:Doe affiliation:Stanford') == {ds_stanford.identifier}
