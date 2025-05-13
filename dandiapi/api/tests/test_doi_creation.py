from __future__ import annotations

import pytest
from django.db import transaction

from dandiapi.api.models import Version
from dandiapi.api.services.publish import _create_and_update_dois


@pytest.mark.django_db
def test_create_and_update_dois_first_publication(draft_version_factory, mocker):
    """Test creating DOIs for first publication of a dandiset."""
    # Create a draft version without a DOI (simulating first publication)
    draft_version = draft_version_factory()
    draft_version.doi = None
    draft_version.save()

    # Create a new published version
    published_version = Version(
        dandiset=draft_version.dandiset,
        version='1.0.0',
        name=draft_version.name,
        metadata=draft_version.metadata.copy(),
    )
    published_version.save()

    # Mock the DOI functions
    mock_generate_doi_data = mocker.patch('dandiapi.api.datacite.generate_doi_data')
    mock_generate_doi_data.side_effect = [
        # Version DOI with publish event
        (f'10.80507/dandi.{draft_version.dandiset.identifier}/1.0.0', {'data': {'attributes': {}}}),
        # Dandiset DOI with publish event (first publication)
        (f'10.80507/dandi.{draft_version.dandiset.identifier}', {'data': {'attributes': {}}}),
    ]

    mock_create_or_update_doi = mocker.patch('dandiapi.api.datacite.create_or_update_doi')

    # Run the function
    with transaction.atomic():
        _create_and_update_dois(published_version.id)

    # Verify that generate_doi_data was called with the right parameters
    assert mock_generate_doi_data.call_count == 2

    # First call should be for the Version DOI with publish event
    version_doi_call = mock_generate_doi_data.call_args_list[0]
    assert version_doi_call[1]['version'] == published_version
    assert version_doi_call[1]['version_doi'] is True
    assert version_doi_call[1]['event'] == 'publish'

    # Second call should be for the Dandiset DOI with publish event (first publication)
    dandiset_doi_call = mock_generate_doi_data.call_args_list[1]
    assert dandiset_doi_call[1]['version'] == published_version
    assert dandiset_doi_call[1]['version_doi'] is False
    assert dandiset_doi_call[1]['event'] == 'publish'

    # Verify that create_or_update_doi was called twice
    assert mock_create_or_update_doi.call_count == 2


@pytest.mark.django_db
def test_create_and_update_dois_subsequent_publication(draft_version_factory, mocker):
    """Test updating DOIs for subsequent publication of a dandiset."""
    # Create a draft version with an existing DOI (simulating a subsequent publication)
    draft_version = draft_version_factory()
    existing_doi = f'10.80507/dandi.{draft_version.dandiset.identifier}'
    draft_version.doi = existing_doi
    draft_version.save()

    # Create a new published version
    published_version = Version(
        dandiset=draft_version.dandiset,
        version='2.0.0',
        name=draft_version.name,
        metadata=draft_version.metadata.copy(),
    )
    published_version.save()

    # Mock the DOI functions
    mock_generate_doi_data = mocker.patch('dandiapi.api.datacite.generate_doi_data')
    mock_generate_doi_data.side_effect = [
        # Version DOI with publish event
        (f'10.80507/dandi.{draft_version.dandiset.identifier}/2.0.0', {'data': {'attributes': {}}}),
        # Dandiset DOI with publish event (updating existing DOI)
        (existing_doi, {'data': {'attributes': {}}}),
    ]

    mock_create_or_update_doi = mocker.patch('dandiapi.api.datacite.create_or_update_doi')

    # Run the function
    with transaction.atomic():
        _create_and_update_dois(published_version.id)

    # Verify that generate_doi_data was called with the right parameters
    assert mock_generate_doi_data.call_count == 2

    # First call should be for the Version DOI with publish event
    version_doi_call = mock_generate_doi_data.call_args_list[0]
    assert version_doi_call[1]['version'] == published_version
    assert version_doi_call[1]['version_doi'] is True
    assert version_doi_call[1]['event'] == 'publish'

    # Second call should be for the Dandiset DOI with publish event (updating)
    dandiset_doi_call = mock_generate_doi_data.call_args_list[1]
    assert dandiset_doi_call[1]['version'] == published_version
    assert dandiset_doi_call[1]['version_doi'] is False
    assert dandiset_doi_call[1]['event'] == 'publish'

    # Verify that create_or_update_doi was called twice
    assert mock_create_or_update_doi.call_count == 2

    # Verify that the DOI values were stored correctly
    published_version.refresh_from_db()
    draft_version.refresh_from_db()
    assert published_version.doi == f'10.80507/dandi.{draft_version.dandiset.identifier}/2.0.0'
    assert draft_version.doi == existing_doi
