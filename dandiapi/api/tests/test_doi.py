from __future__ import annotations

import pytest
from django.conf import settings
from dandischema.datacite import to_datacite

from dandiapi.api import datacite
from dandiapi.api.models import Version


@pytest.mark.django_db
def test_generate_doi_data_version_doi_draft_event(published_version):
    """Test generating a Version DOI with draft event."""
    doi_string, datacite_payload = datacite.generate_doi_data(
        version=published_version, version_doi=True, event=None
    )
    
    # Verify DOI string format for Version DOI
    dandiset_id = published_version.dandiset.identifier
    version_id = published_version.version
    prefix = settings.DANDI_DOI_API_PREFIX or '10.80507'
    expected_doi = f'{prefix}/dandi.{dandiset_id}/{version_id}'
    assert doi_string == expected_doi
    
    # Verify payload properties
    assert datacite_payload['data']['attributes']['doi'] == expected_doi
    assert datacite_payload['data']['attributes']['url'] == published_version.metadata['url']
    # For draft event, the 'event' field should be None or not present
    assert datacite_payload['data']['attributes'].get('event') is None


@pytest.mark.django_db
def test_generate_doi_data_version_doi_publish_event(published_version):
    """Test generating a Version DOI with publish event."""
    doi_string, datacite_payload = datacite.generate_doi_data(
        version=published_version, version_doi=True, event="publish"
    )
    
    # Verify DOI string format for Version DOI
    dandiset_id = published_version.dandiset.identifier
    version_id = published_version.version
    prefix = settings.DANDI_DOI_API_PREFIX or '10.80507'
    expected_doi = f'{prefix}/dandi.{dandiset_id}/{version_id}'
    assert doi_string == expected_doi
    
    # Verify payload properties
    assert datacite_payload['data']['attributes']['doi'] == expected_doi
    assert datacite_payload['data']['attributes']['url'] == published_version.metadata['url']
    assert datacite_payload['data']['attributes']['event'] == "publish"


@pytest.mark.django_db
def test_generate_doi_data_version_doi_hide_event(published_version):
    """Test generating a Version DOI with hide event."""
    doi_string, datacite_payload = datacite.generate_doi_data(
        version=published_version, version_doi=True, event="hide"
    )
    
    # Verify DOI string format for Version DOI
    dandiset_id = published_version.dandiset.identifier
    version_id = published_version.version
    prefix = settings.DANDI_DOI_API_PREFIX or '10.80507'
    expected_doi = f'{prefix}/dandi.{dandiset_id}/{version_id}'
    assert doi_string == expected_doi
    
    # Verify payload properties
    assert datacite_payload['data']['attributes']['doi'] == expected_doi
    assert datacite_payload['data']['attributes']['url'] == published_version.metadata['url']
    assert datacite_payload['data']['attributes']['event'] == "hide"


@pytest.mark.django_db
def test_generate_doi_data_dandiset_doi_draft_event(published_version):
    """Test generating a Dandiset DOI with draft event."""
    doi_string, datacite_payload = datacite.generate_doi_data(
        version=published_version, version_doi=False, event=None
    )
    
    # Verify DOI string format for Dandiset DOI
    dandiset_id = published_version.dandiset.identifier
    prefix = settings.DANDI_DOI_API_PREFIX or '10.80507'
    expected_doi = f'{prefix}/dandi.{dandiset_id}'
    assert doi_string == expected_doi
    
    # Verify payload properties
    assert datacite_payload['data']['attributes']['doi'] == expected_doi
    # URL should be the Dandiset URL (without version)
    expected_url = published_version.metadata['url'].rsplit('/', 1)[0]
    assert datacite_payload['data']['attributes']['url'] == expected_url
    # For draft event, the 'event' field should be None or not present
    assert datacite_payload['data']['attributes'].get('event') is None


@pytest.mark.django_db
def test_generate_doi_data_dandiset_doi_publish_event(published_version):
    """Test generating a Dandiset DOI with publish event."""
    doi_string, datacite_payload = datacite.generate_doi_data(
        version=published_version, version_doi=False, event="publish"
    )
    
    # Verify DOI string format for Dandiset DOI
    dandiset_id = published_version.dandiset.identifier
    prefix = settings.DANDI_DOI_API_PREFIX or '10.80507'
    expected_doi = f'{prefix}/dandi.{dandiset_id}'
    assert doi_string == expected_doi
    
    # Verify payload properties
    assert datacite_payload['data']['attributes']['doi'] == expected_doi
    # URL should be the Dandiset URL (without version)
    expected_url = published_version.metadata['url'].rsplit('/', 1)[0]
    assert datacite_payload['data']['attributes']['url'] == expected_url
    assert datacite_payload['data']['attributes']['event'] == "publish"


@pytest.mark.django_db
def test_generate_doi_data_dandiset_doi_hide_event(published_version):
    """Test generating a Dandiset DOI with hide event."""
    doi_string, datacite_payload = datacite.generate_doi_data(
        version=published_version, version_doi=False, event="hide"
    )
    
    # Verify DOI string format for Dandiset DOI
    dandiset_id = published_version.dandiset.identifier
    prefix = settings.DANDI_DOI_API_PREFIX or '10.80507'
    expected_doi = f'{prefix}/dandi.{dandiset_id}'
    assert doi_string == expected_doi
    
    # Verify payload properties
    assert datacite_payload['data']['attributes']['doi'] == expected_doi
    # URL should be the Dandiset URL (without version)
    expected_url = published_version.metadata['url'].rsplit('/', 1)[0]
    assert datacite_payload['data']['attributes']['url'] == expected_url
    assert datacite_payload['data']['attributes']['event'] == "hide"


@pytest.mark.django_db
def test_generate_doi_data_url_handling_version_doi(published_version):
    """Test URL handling for Version DOIs."""
    _, datacite_payload = doi.generate_doi_data(
        version=published_version, version_doi=True
    )
    
    # URL should be the complete Version URL (with version)
    expected_url = published_version.metadata['url']
    assert datacite_payload['data']['attributes']['url'] == expected_url


@pytest.mark.django_db
def test_generate_doi_data_url_handling_dandiset_doi(published_version):
    """Test URL handling for Dandiset DOIs."""
    _, datacite_payload = doi.generate_doi_data(
        version=published_version, version_doi=False
    )
    
    # URL should be the Dandiset URL (without version)
    expected_url = published_version.metadata['url'].rsplit('/', 1)[0]
    assert datacite_payload['data']['attributes']['url'] == expected_url


@pytest.mark.django_db
def test_datacite_payload_structure(published_version):
    """Test the structure of the datacite payload."""
    _, datacite_payload = doi.generate_doi_data(
        version=published_version, version_doi=True
    )
    
    # Test the basic structure of the payload
    assert 'data' in datacite_payload
    assert 'attributes' in datacite_payload['data']
    assert 'type' in datacite_payload['data']
    assert datacite_payload['data']['type'] == 'dois'
    
    # Test that to_datacite was called correctly by checking required fields
    attributes = datacite_payload['data']['attributes']
    assert 'titles' in attributes
    assert 'creators' in attributes
    assert 'publisher' in attributes
    assert 'publicationYear' in attributes
    assert 'types' in attributes
    assert 'url' in attributes