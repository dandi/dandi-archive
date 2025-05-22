from __future__ import annotations

import pytest

from dandiapi.api.doi import _create_dandiset_draft_doi


@pytest.mark.django_db
def test__create_dandiset_draft_doi(draft_version, mocker):
    """Test the _create_dandiset_draft_doi function directly."""
    # Set up mocks
    mock_generate_doi = mocker.patch('dandiapi.api.doi.generate_doi_data')
    mock_generate_doi.return_value = ('10.48324/dandi.000123', {'data': {'attributes': {}}})

    mock_create_doi = mocker.patch('dandiapi.api.doi.create_or_update_doi')
    mock_create_doi.return_value = '10.48324/dandi.000123'

    # Call the function directly
    _create_dandiset_draft_doi(draft_version)

    # Verify the mocks were called correctly
    mock_generate_doi.assert_called_once_with(
        draft_version,
        version_doi=False,
        event=None  # Draft DOI
    )
    mock_create_doi.assert_called_once_with({'data': {'attributes': {}}})

    # Verify the DOI was stored in the draft version
    assert draft_version.doi == '10.48324/dandi.000123'