"""HTTP-level DataCite client tests using `responses` to mock requests.

These tests exercise the actual `datacite_session()` retry adapter, the
`generate_doi_data()` payload builder, and the service-layer error handling
— paths that `test_doi_lifecycle.py` mocks at a higher level.

Note: AI-generated (Claude Code).
"""

from __future__ import annotations

import re

from django.test import override_settings
import pytest
import responses

from dandiapi.api.services.doi import (
    create_dandiset_doi,
    delete_dandiset_doi,
)
from dandiapi.api.services.doi.exceptions import DataCiteAPIError
from dandiapi.api.services.doi.utils import format_doi, get_doi_url
from dandiapi.api.tests.factories import DraftVersionFactory

DOI_API_URL = 'https://api.test.datacite.org/dois'
DOI_SETTINGS = {
    'DANDI_DOI_API_URL': DOI_API_URL,
    'DANDI_DOI_API_USER': 'test-user',
    'DANDI_DOI_API_PASSWORD': 'test-password',
    'DANDI_DOI_API_PREFIX': '10.80507',
    'DANDI_DOI_PUBLISH': False,
}


@pytest.fixture
def configured_dandiset(db, mocker):
    """Create a draft version with metadata mocked at the payload-builder layer.

    The factory's metadata isn't a complete PublishedDandiset, so we stub
    `generate_doi_data` to return a deterministic (doi, payload) pair.
    Tests focus on HTTP behavior, not payload generation.
    """
    version = DraftVersionFactory.create()
    dandiset = version.dandiset
    expected_doi = format_doi(dandiset.identifier)
    payload = {'data': {'id': expected_doi, 'type': 'dois', 'attributes': {}}}
    mocker.patch(
        'dandiapi.api.services.doi.generate_doi_data',
        return_value=(expected_doi, payload),
    )
    return dandiset


@pytest.mark.django_db
@override_settings(**DOI_SETTINGS)
@responses.activate
def test_create_dandiset_doi_success_uses_put(configured_dandiset):
    """Concept DOI create issues a PUT (not POST) to the DOI's URL — idempotent retry."""
    expected_doi = format_doi(configured_dandiset.identifier)
    responses.put(
        get_doi_url(expected_doi),
        json={'data': {'id': expected_doi, 'attributes': {'state': 'draft'}}},
        status=201,
    )
    create_dandiset_doi(configured_dandiset)

    assert len(responses.calls) == 1
    assert responses.calls[0].request.method == 'PUT'
    assert expected_doi in responses.calls[0].request.url


@pytest.mark.django_db
@override_settings(**DOI_SETTINGS)
@responses.activate
def test_create_dandiset_doi_retries_on_503(configured_dandiset):
    """urllib3 Retry adapter retries 5xx — burns through transient failures."""
    expected_doi = format_doi(configured_dandiset.identifier)
    url = get_doi_url(expected_doi)
    responses.put(url, status=503)
    responses.put(url, status=503)
    responses.put(
        url,
        json={'data': {'id': expected_doi, 'attributes': {'state': 'draft'}}},
        status=201,
    )
    create_dandiset_doi(configured_dandiset)

    assert len(responses.calls) == 3


@pytest.mark.django_db
@override_settings(**DOI_SETTINGS)
@responses.activate
def test_create_dandiset_doi_422_raises(configured_dandiset):
    """4xx (non-429) raises DataCiteAPIError without retry — task layer marks failed."""
    expected_doi = format_doi(configured_dandiset.identifier)
    responses.put(
        get_doi_url(expected_doi),
        json={'errors': [{'title': 'Validation failed'}]},
        status=422,
    )
    with pytest.raises(DataCiteAPIError):
        create_dandiset_doi(configured_dandiset)
    assert len(responses.calls) == 1


@pytest.mark.django_db
@override_settings(**DOI_SETTINGS)
@responses.activate
def test_create_dandiset_doi_429_then_success(configured_dandiset):
    """429 with Retry-After is honored by urllib3 status_forcelist; eventual success."""
    expected_doi = format_doi(configured_dandiset.identifier)
    url = get_doi_url(expected_doi)
    responses.put(url, status=429, headers={'Retry-After': '1'})
    responses.put(
        url,
        json={'data': {'id': expected_doi, 'attributes': {'state': 'draft'}}},
        status=201,
    )
    create_dandiset_doi(configured_dandiset)
    assert len(responses.calls) == 2


@pytest.mark.django_db
@override_settings(**DOI_SETTINGS)
@responses.activate
def test_delete_dandiset_doi_404_silenced():
    """404 on delete is logged and silenced (DOI never registered)."""
    doi = '10.80507/dandi.000123'
    responses.delete(get_doi_url(doi), status=404)
    delete_dandiset_doi(doi)
    assert len(responses.calls) == 1


@pytest.mark.django_db
@override_settings(**DOI_SETTINGS)
@responses.activate
def test_hide_published_version_doi_task_404_silenced():
    """hide_published_version_doi_task swallows 404 (already deleted from DataCite)."""
    from dandiapi.api.tasks import hide_published_version_doi_task

    doi = '10.80507/dandi.000123/0.250101.0001'
    responses.put(get_doi_url(doi), status=404)
    hide_published_version_doi_task(doi)
    assert len(responses.calls) == 1


@pytest.mark.django_db
@override_settings(**DOI_SETTINGS)
@responses.activate
def test_hide_published_version_doi_task_other_error_raises():
    """Non-404 error during hide propagates so Celery can retry."""
    from dandiapi.api.tasks import hide_published_version_doi_task

    doi = '10.80507/dandi.000123/0.250101.0001'
    responses.put(get_doi_url(doi), status=410, json={'errors': [{'title': 'gone'}]})
    with pytest.raises(DataCiteAPIError):
        hide_published_version_doi_task(doi)


@pytest.mark.django_db
@override_settings(**DOI_SETTINGS)
@responses.activate
def test_create_dandiset_doi_task_state_transition_success(configured_dandiset):
    """End-to-end: concept-DOI create task drives doi_state pending → draft."""
    from dandiapi.api.models import Version
    from dandiapi.api.tasks import create_dandiset_doi_task

    expected_doi = format_doi(configured_dandiset.identifier)
    Version.objects.filter(dandiset=configured_dandiset, version='draft').update(
        doi=expected_doi, doi_state='pending'
    )
    configured_dandiset.concept_doi = expected_doi
    configured_dandiset.save()

    responses.put(
        get_doi_url(expected_doi),
        json={'data': {'id': expected_doi, 'attributes': {'state': 'draft'}}},
        status=201,
    )

    create_dandiset_doi_task.apply(args=[configured_dandiset.id], throw=True)

    version = Version.objects.get(dandiset=configured_dandiset, version='draft')
    assert version.doi_state == 'draft'


@pytest.mark.django_db
@override_settings(**DOI_SETTINGS)
@responses.activate
def test_create_dandiset_doi_task_state_transition_4xx_failure(configured_dandiset):
    """End-to-end: 4xx surfaces as DataCiteAPIError, task marks doi_state failed."""
    from dandiapi.api.models import Version
    from dandiapi.api.tasks import create_dandiset_doi_task

    expected_doi = format_doi(configured_dandiset.identifier)
    Version.objects.filter(dandiset=configured_dandiset, version='draft').update(
        doi=expected_doi, doi_state='pending'
    )
    configured_dandiset.concept_doi = expected_doi
    configured_dandiset.save()

    responses.put(
        get_doi_url(expected_doi),
        json={'errors': [{'title': 'Validation failed'}]},
        status=422,
    )

    with pytest.raises(DataCiteAPIError):
        create_dandiset_doi_task.apply(args=[configured_dandiset.id], throw=True)

    version = Version.objects.get(dandiset=configured_dandiset, version='draft')
    assert version.doi_state == 'failed'


@pytest.mark.django_db
@override_settings(**DOI_SETTINGS)
@responses.activate
def test_datacite_session_includes_auth_and_headers():
    """datacite_session() applies HTTPBasicAuth and JSON-API headers per request."""
    doi = '10.80507/dandi.000123'
    responses.delete(get_doi_url(doi), status=404)
    delete_dandiset_doi(doi)
    req = responses.calls[0].request
    assert req.headers['Accept'] == 'application/vnd.api+json'
    assert req.headers['Content-Type'] == 'application/vnd.api+json'
    assert re.match(r'^Basic ', req.headers['Authorization'])
