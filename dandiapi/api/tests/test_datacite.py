from __future__ import annotations

from django.conf import settings
import pytest
from requests.exceptions import HTTPError

from dandiapi.api.datacite import DataCiteClient


@pytest.fixture(autouse=True)
def mock_requests(mocker):
    """Mock individual request methods for all tests to prevent actual HTTP calls."""
    # Create a mock object to hold all the request methods
    mock_obj = mocker.Mock()

    # Patch the individual methods
    mock_obj.get = mocker.patch('requests.get')
    mock_obj.post = mocker.patch('requests.post')
    mock_obj.put = mocker.patch('requests.put')
    mock_obj.delete = mocker.patch('requests.delete')

    # Return the mock object with all methods
    return mock_obj


@pytest.fixture
def datacite_client():
    return DataCiteClient()


@pytest.fixture
def datacite_client_unsafe():
    """Bypass safety feature that prevents API calls to datacite during tests."""
    client = DataCiteClient()
    if hasattr(client.create_or_update_doi, '__wrapped__'):
        client.create_or_update_doi = client.create_or_update_doi.__wrapped__.__get__(client)
    if hasattr(client.delete_or_hide_doi, '__wrapped__'):
        client.delete_or_hide_doi = client.delete_or_hide_doi.__wrapped__.__get__(client)

    return client


def test_is_configured(datacite_client, mocker):
    """Test the is_configured method."""
    # Test when all settings are configured
    # We need to patch the DANDI_DOI_SETTINGS list directly since it's imported at module level
    mocked_settings = [
        ('https://api.test', 'DANDI_DOI_API_URL'),
        ('user', 'DANDI_DOI_API_USER'),
        ('pass', 'DANDI_DOI_API_PASSWORD'),
        ('10.12345', 'DANDI_DOI_API_PREFIX'),
    ]
    mocker.patch('dandiapi.api.datacite.DANDI_DOI_SETTINGS', mocked_settings)

    assert datacite_client.is_configured() is True

    # Test when one setting is not configured
    mocked_settings_with_none = [
        (None, 'DANDI_DOI_API_URL'),
        ('user', 'DANDI_DOI_API_USER'),
        ('pass', 'DANDI_DOI_API_PASSWORD'),
        ('10.12345', 'DANDI_DOI_API_PREFIX'),
    ]
    mocker.patch('dandiapi.api.datacite.DANDI_DOI_SETTINGS', mocked_settings_with_none)
    assert datacite_client.is_configured() is False


def test_format_doi(datacite_client, mocker):
    """Test formatting DOI strings."""
    mocker.patch.object(datacite_client, 'api_prefix', '10.12345')

    # Test Version DOI format
    version_doi = datacite_client.format_doi('000123', '1.2.3')
    assert version_doi == '10.12345/dandi.000123/1.2.3'

    # Test Dandiset DOI format
    dandiset_doi = datacite_client.format_doi('000123')
    assert dandiset_doi == '10.12345/dandi.000123'


@pytest.mark.django_db
def test_generate_doi_data(datacite_client, published_version, mocker):
    """Test generating DOI data for a version."""
    # Mock to_datacite to avoid actual validation
    mock_to_datacite = mocker.patch('dandischema.datacite.to_datacite')
    mock_to_datacite.return_value = {'data': {'attributes': {}}}

    # Test Version DOI
    doi_string, payload = datacite_client.generate_doi_data(published_version, version_doi=True)
    dandiset_id = published_version.dandiset.identifier
    version_id = published_version.version
    expected_doi = f'{datacite_client.api_prefix}/dandi.{dandiset_id}/{version_id}'
    assert doi_string == expected_doi
    assert 'doi' in published_version.metadata
    # Make sure metadata is copied, not modified
    assert id(published_version.metadata) != id(
        datacite_client.generate_doi_data(published_version)[1]
    )

    # Test Dandiset DOI
    doi_string, payload = datacite_client.generate_doi_data(published_version, version_doi=False)
    expected_doi = f'{datacite_client.api_prefix}/dandi.{dandiset_id}'
    assert doi_string == expected_doi


def test_create_or_update_doi_not_configured(datacite_client_unsafe, mock_requests, mocker):
    """Test create_or_update_doi when API is not configured."""
    mocker.patch.object(datacite_client_unsafe, 'is_configured', return_value=False)
    mock_logger = mocker.patch('dandiapi.api.datacite.logger')

    payload = {'data': {'attributes': {'doi': '10.12345/test'}}}
    result = datacite_client_unsafe.create_or_update_doi(payload)

    assert result is None

    # Verify no requests methods were called
    assert not mock_requests.get.called
    assert not mock_requests.post.called
    assert not mock_requests.put.called
    assert not mock_requests.delete.called
    # Check that only the warning was logged
    mock_logger.warning.assert_called_once()


def test_create_or_update_doi_publish_disabled_event_publish(
    datacite_client_unsafe, mock_requests, mocker
):
    """Test create_or_update_doi when DANDI_DOI_PUBLISH is False."""
    mocker.patch.object(datacite_client_unsafe, 'is_configured', return_value=True)
    mocker.patch.object(settings, 'DANDI_DOI_PUBLISH', new=False)
    mock_logger = mocker.patch('dandiapi.api.datacite.logger')

    # Configure mock response
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    mock_requests.post.return_value = mock_response

    # Test with publish event
    payload = {
        'data': {
            'attributes': {
                'doi': '10.12345/test',
                'event': 'publish',
            }
        }
    }
    datacite_client_unsafe.create_or_update_doi(payload)

    expected_payload = {
        'data': {
            'attributes': {
                'doi': '10.12345/test',
                # event should be removed by the code
            }
        }
    }
    mock_requests.post.assert_called_once()
    assert mock_requests.post.call_args[1]['json'] == expected_payload
    mock_logger.warning.assert_called_once()
    # Verify no other requests methods were called
    assert not mock_requests.get.called
    assert not mock_requests.put.called
    assert not mock_requests.delete.called


def test_create_or_update_doi_new_doi(datacite_client_unsafe, mock_requests, mocker):
    """Test creating a new DOI successfully."""
    mocker.patch.object(datacite_client_unsafe, 'is_configured', return_value=True)
    mocker.patch.object(settings, 'DANDI_DOI_PUBLISH', new=True)

    # Configure mock response
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    mock_requests.post.return_value = mock_response

    payload = {'data': {'attributes': {'doi': '10.12345/test', 'event': 'publish'}}}
    result = datacite_client_unsafe.create_or_update_doi(payload)

    # Verify POST was called with correct params
    assert mock_requests.post.called
    assert mock_requests.post.call_args[1]['json'] == payload
    assert mock_requests.post.call_args[1]['auth'] == datacite_client_unsafe.auth
    assert mock_requests.post.call_args[1]['headers'] == datacite_client_unsafe.headers
    assert mock_requests.post.call_args[1]['timeout'] == datacite_client_unsafe.timeout
    # Verify no other requests methods were called
    assert not mock_requests.get.called
    assert not mock_requests.put.called
    assert not mock_requests.delete.called
    assert result == '10.12345/test'


def test_create_or_update_doi_existing_doi(datacite_client_unsafe, mock_requests, mocker):
    """Test updating an existing DOI."""
    mocker.patch.object(datacite_client_unsafe, 'is_configured', return_value=True)
    mocker.patch.object(settings, 'DANDI_DOI_PUBLISH', new=True)

    # Mock POST to fail with 422 (already exists)
    mock_post_response = mocker.Mock()
    http_error = HTTPError('DOI already exists')
    http_error.response = mocker.Mock()
    http_error.response.status_code = 422
    mock_post_response.raise_for_status.side_effect = http_error
    mock_requests.post.return_value = mock_post_response

    # Mock PUT to succeed
    mock_put_response = mocker.Mock()
    mock_put_response.raise_for_status = mocker.Mock()
    mock_requests.put.return_value = mock_put_response

    payload = {'data': {'attributes': {'doi': '10.12345/test'}}}
    result = datacite_client_unsafe.create_or_update_doi(payload)

    assert mock_requests.post.called
    # Verify PUT was called with correct params
    assert mock_requests.put.called
    assert mock_requests.put.call_args[1]['json'] == payload
    # Verify no other HTTP methods besides post and put were called
    assert not mock_requests.get.called
    assert not mock_requests.delete.called
    assert result == '10.12345/test'


def test_create_or_update_doi_post_error(datacite_client_unsafe, mock_requests, mocker):
    """Test error handling when POST fails with non-422 error."""
    mocker.patch.object(datacite_client_unsafe, 'is_configured', return_value=True)
    mock_logger = mocker.patch('dandiapi.api.datacite.logger')

    # Mock POST to fail with 400
    http_error = HTTPError('Bad request')
    http_error.response = mocker.Mock()
    http_error.response.status_code = 400
    http_error.response.text = 'Bad request'
    mock_requests.post.side_effect = http_error

    payload = {'data': {'attributes': {'doi': '10.12345/test'}}}
    with pytest.raises(HTTPError):
        datacite_client_unsafe.create_or_update_doi(payload)

    # Verify logger was called
    mock_logger.exception.assert_called_once()
    # Verify no other HTTP methods were called
    assert not mock_requests.get.called
    assert not mock_requests.put.called
    assert not mock_requests.delete.called


def test_create_or_update_doi_put_error(datacite_client_unsafe, mock_requests, mocker):
    """Test error handling when PUT fails."""
    mocker.patch.object(datacite_client_unsafe, 'is_configured', return_value=True)
    mock_logger = mocker.patch('dandiapi.api.datacite.logger')

    # Mock POST to fail with 422 (already exists)
    mock_post_response = mocker.Mock()
    http_error = HTTPError('DOI already exists')
    http_error.response = mocker.Mock()
    http_error.response.status_code = 422
    mock_post_response.raise_for_status.side_effect = http_error
    mock_requests.post.return_value = mock_post_response

    # Mock PUT to fail
    put_error = HTTPError('Update failed')
    put_error.response = mocker.Mock()
    put_error.response.text = 'Update failed'
    mock_requests.put.side_effect = put_error

    payload = {'data': {'attributes': {'doi': '10.12345/test'}}}
    with pytest.raises(HTTPError):
        datacite_client_unsafe.create_or_update_doi(payload)

    # Verify both methods were called in the right order
    assert mock_requests.post.called
    assert mock_requests.put.called
    # Verify no other HTTP methods were called
    assert not mock_requests.get.called
    assert not mock_requests.delete.called
    # Verify logger was called
    mock_logger.exception.assert_called_once()


def test_delete_or_hide_doi_not_configured(datacite_client_unsafe, mock_requests, mocker):
    """Test delete_or_hide_doi when API is not configured."""
    mocker.patch.object(datacite_client_unsafe, 'is_configured', return_value=False)
    mock_logger = mocker.patch('dandiapi.api.datacite.logger')

    datacite_client_unsafe.delete_or_hide_doi('10.12345/test')

    # Verify no HTTP methods were called
    assert not mock_requests.get.called
    assert not mock_requests.post.called
    assert not mock_requests.put.called
    assert not mock_requests.delete.called
    mock_logger.warning.assert_called_once()


def test_delete_or_hide_doi_draft(datacite_client_unsafe, mock_requests, mocker):
    """Test deleting a draft DOI."""
    mocker.patch.object(datacite_client_unsafe, 'is_configured', return_value=True)
    mock_logger = mocker.patch('dandiapi.api.datacite.logger')

    # Mock GET to return a draft DOI
    mock_get_response = mocker.Mock()
    mock_get_response.json.return_value = {'data': {'attributes': {'state': 'draft'}}}
    mock_get_response.raise_for_status = mocker.Mock()
    mock_requests.get.return_value = mock_get_response

    # Mock DELETE to succeed
    mock_delete_response = mocker.Mock()
    mock_delete_response.raise_for_status = mocker.Mock()
    mock_requests.delete.return_value = mock_delete_response

    datacite_client_unsafe.delete_or_hide_doi('10.12345/test')

    # Verify GET and DELETE were called
    assert mock_requests.get.called
    assert mock_requests.delete.called
    assert '10.12345/test' in mock_requests.delete.call_args[0][0]
    # Verify no other HTTP methods were called
    assert not mock_requests.post.called
    assert not mock_requests.put.called
    mock_logger.info.assert_called_once()


def test_delete_or_hide_doi_findable_publish_enabled(datacite_client_unsafe, mock_requests, mocker):
    """Test hiding a findable DOI when DANDI_DOI_PUBLISH is True."""
    mocker.patch.object(datacite_client_unsafe, 'is_configured', return_value=True)
    mocker.patch.object(settings, 'DANDI_DOI_PUBLISH', new=True)
    mock_logger = mocker.patch('dandiapi.api.datacite.logger')

    # Mock GET to return a findable DOI
    mock_get_response = mocker.Mock()
    mock_get_response.json.return_value = {'data': {'attributes': {'state': 'findable'}}}
    mock_get_response.raise_for_status = mocker.Mock()
    mock_requests.get.return_value = mock_get_response

    # Mock PUT to succeed
    mock_put_response = mocker.Mock()
    mock_put_response.raise_for_status = mocker.Mock()
    mock_requests.put.return_value = mock_put_response

    datacite_client_unsafe.delete_or_hide_doi('10.12345/test')

    # Verify GET and PUT were called, but not other methods
    assert mock_requests.get.called
    assert mock_requests.put.called
    assert not mock_requests.post.called
    assert not mock_requests.delete.called

    # Verify correct parameters
    assert '10.12345/test' in mock_requests.put.call_args[0][0]
    assert mock_requests.put.call_args[1]['json']['data']['attributes']['event'] == 'hide'
    mock_logger.info.assert_called_once()


def test_delete_or_hide_doi_findable_publish_disabled(
    datacite_client_unsafe, mock_requests, mocker
):
    """Test not hiding a findable DOI when DANDI_DOI_PUBLISH is False."""
    mocker.patch.object(datacite_client_unsafe, 'is_configured', return_value=True)
    mocker.patch.object(settings, 'DANDI_DOI_PUBLISH', new=False)
    mock_logger = mocker.patch('dandiapi.api.datacite.logger')

    # Mock GET to return a findable DOI
    mock_get_response = mocker.Mock()
    mock_get_response.json.return_value = {'data': {'attributes': {'state': 'findable'}}}
    mock_get_response.raise_for_status = mocker.Mock()
    mock_requests.get.return_value = mock_get_response

    datacite_client_unsafe.delete_or_hide_doi('10.12345/test')

    # Verify only GET was called, but no other methods
    assert mock_requests.get.called
    assert not mock_requests.post.called
    assert not mock_requests.put.called
    assert not mock_requests.delete.called
    mock_logger.warning.assert_called_once()


def test_delete_or_hide_doi_nonexistent(datacite_client_unsafe, mock_requests, mocker):
    """Test handling a nonexistent DOI."""
    mocker.patch.object(datacite_client_unsafe, 'is_configured', return_value=True)
    mock_logger = mocker.patch('dandiapi.api.datacite.logger')

    # Mock GET to fail with 404
    get_error = HTTPError('Not found')
    get_error.response = mocker.Mock()
    get_error.response.status_code = 404
    mock_requests.get.side_effect = get_error

    datacite_client_unsafe.delete_or_hide_doi('10.12345/test')

    # Verify only GET was attempted, but no other methods
    assert mock_requests.get.called
    assert not mock_requests.post.called
    assert not mock_requests.put.called
    assert not mock_requests.delete.called
    mock_logger.warning.assert_called_once()


def test_delete_or_hide_doi_get_error(datacite_client_unsafe, mock_requests, mocker):
    """Test error handling when GET fails with non-404 error."""
    mocker.patch.object(datacite_client_unsafe, 'is_configured', return_value=True)
    mock_logger = mocker.patch('dandiapi.api.datacite.logger')

    # Mock GET to fail with 500
    get_error = HTTPError('Server error')
    get_error.response = mocker.Mock()
    get_error.response.status_code = 500
    mock_requests.get.side_effect = get_error

    with pytest.raises(HTTPError):
        datacite_client_unsafe.delete_or_hide_doi('10.12345/test')

    # Verify only GET was attempted, but no other methods
    assert mock_requests.get.called
    assert not mock_requests.post.called
    assert not mock_requests.put.called
    assert not mock_requests.delete.called
    mock_logger.exception.assert_called_once()
