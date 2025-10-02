from __future__ import annotations

import pytest

from dandiapi.api.doi import _create_dandiset_draft_doi, _update_draft_version_doi


@pytest.mark.django_db
def test__create_dandiset_draft_doi(draft_version, mocker):
    """Test the _create_dandiset_draft_doi function directly."""
    # Set up mocks
    mock_generate_doi = mocker.patch('dandiapi.api.services.doi.utils.generate_doi_data')
    mock_generate_doi.return_value = ('10.48324/dandi.000123', {'data': {'attributes': {}}})

    mock_create_doi = mocker.patch('dandiapi.api.services.doi.create_dandiset_doi')
    mock_create_doi.return_value = '10.48324/dandi.000123'

    # Call the function directly
    _create_dandiset_draft_doi(draft_version)

    # Verify the mocks were called correctly
    mock_generate_doi.assert_called_once_with(
        draft_version,
        version_doi=False,
        event=None,  # Draft DOI
    )
    mock_create_doi.assert_called_once_with({'data': {'attributes': {}}})

    # Verify the DOI was stored in the draft version
    assert draft_version.doi == '10.48324/dandi.000123'


@pytest.mark.django_db
def test_update_draft_version_doi_no_previous_doi(draft_version, mocker):
    """Test updating a draft DOI when none exists yet."""
    # Set up mocks
    mock_generate_doi = mocker.patch('dandiapi.api.services.doi.utils.generate_doi_data')
    mock_generate_doi.return_value = ('10.48324/dandi.000123', {'data': {'attributes': {}}})

    mock_create_doi = mocker.patch('dandiapi.api.services.doi.update_dandiset_doi')
    mock_create_doi.return_value = '10.48324/dandi.000123'

    _update_draft_version_doi(draft_version)

    # Verify the mocks were called correctly
    mock_generate_doi.assert_called_once_with(draft_version, version_doi=False, event=None)
    mock_create_doi.assert_called_once_with({'data': {'attributes': {}}})

    # Verify the DOI was stored in the draft version
    assert draft_version.doi == '10.48324/dandi.000123'


@pytest.mark.django_db
def test_update_draft_version_doi_existing_doi(draft_version, mocker):
    """Test updating a draft DOI when one already exists."""
    # Set existing DOI
    draft_version.doi = '10.48324/dandi.000123'
    draft_version.save()

    # Set up mocks
    mock_generate_doi = mocker.patch('dandiapi.api.services.doi.utils.generate_doi_data')
    mock_generate_doi.return_value = ('10.48324/dandi.000123', {'data': {'attributes': {}}})

    mock_create_doi = mocker.patch('dandiapi.api.services.doi.update_dandiset_doi')
    mock_create_doi.return_value = '10.48324/dandi.000123'

    _update_draft_version_doi(draft_version)

    # Verify the mocks were called correctly
    mock_generate_doi.assert_called_once_with(draft_version, version_doi=False, event=None)
    mock_create_doi.assert_called_once_with({'data': {'attributes': {}}})

    # Verify the DOI is still the same
    assert draft_version.doi == '10.48324/dandi.000123'


@pytest.mark.django_db
def test_update_draft_version_doi_published_version(draft_version, published_version, mocker):
    """Test that update_draft_version_doi is a no-op for dandisets with published versions."""
    # Set up mocks
    mock_generate_doi = mocker.patch('dandiapi.api.services.doi.utils.generate_doi_data')
    mock_create_doi = mocker.patch('dandiapi.api.services.doi.update_dandiset_doi')

    _update_draft_version_doi(draft_version)

    # Verify no DOI operations were performed
    mock_generate_doi.assert_not_called()
    mock_create_doi.assert_not_called()
