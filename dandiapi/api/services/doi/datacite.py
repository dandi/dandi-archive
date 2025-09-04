"""
DataCite service functions.

This module provides service functions for interacting with the DataCite API,
refactored from the original datacite.py implementation and incorporating
DOI management functions from doi.py.
"""

from __future__ import annotations

import copy
import logging

from django.conf import settings
import requests
import requests.auth

from .exceptions import (
    DataCiteAPIError,
    DataCitePublishNotEnabledError,
)
from .utils import (
    _validate_configuration,
    _validate_publish_enabled,
    block_during_test,
    raise_datacite_exception,
)

logger = logging.getLogger(__name__)


def _get_auth() -> requests.auth.HTTPBasicAuth:
    """Get HTTP Basic Auth for DataCite API."""
    return requests.auth.HTTPBasicAuth(settings.DANDI_DOI_API_USER, settings.DANDI_DOI_API_PASSWORD)


def _get_headers() -> dict:
    """Get headers for DataCite API requests."""
    return {'Accept': 'application/vnd.api+json'}


def _get_timeout() -> int:
    """Get timeout for DataCite API requests."""
    return 30


@block_during_test
def create_doi(datacite_payload: dict) -> str:
    """
    Create a new DOI with the DataCite API.

    Args:
        datacite_payload: The DOI payload to send to DataCite.

    Returns:
        The DOI string on success.

    Raises:
        DataCiteNotConfiguredError: If the API is not configured.
        DataCiteAPIError: If the API request fails.
    """
    _validate_configuration()
    payload = copy.deepcopy(datacite_payload)
    doi = payload['data']['attributes']['doi']
    event = payload['data']['attributes'].get('event')

    # Validate publish operations are enabled if needed
    _validate_publish_enabled(event)

    # Remove event to make it a draft DOI if publish is not enabled
    if not settings.DANDI_DOI_PUBLISH and event in ['publish', 'hide']:
        if 'event' in payload['data']['attributes']:
            del payload['data']['attributes']['event']
        logger.warning('DANDI_DOI_PUBLISH is not enabled. DOI %s will be created as draft.', doi)

    response = requests.post(
        settings.DANDI_DOI_API_URL,
        json=payload,
        auth=_get_auth(),
        headers=_get_headers(),
        timeout=_get_timeout(),
    )
    if not response.ok:
        raise_datacite_exception(
            desc=f'Failed to create DOI {doi}',
            response=response,
            payload=payload,
        )

    return doi


@block_during_test
def update_doi(doi: str, datacite_payload: dict) -> str:
    """
    Update an existing DOI with the DataCite API.

    Args:
        doi: The DOI to update.
        datacite_payload: The updated DOI payload.

    Returns:
        The DOI string on success.

    Raises:
        DataCiteNotConfiguredError: If the API is not configured.
        DataCiteAPIError: If the API request fails.
    """
    _validate_configuration()
    payload = copy.deepcopy(datacite_payload)
    event = payload['data']['attributes'].get('event')

    # Validate publish operations are enabled if needed
    _validate_publish_enabled(event)

    # Remove event to make it a draft DOI if publish is not enabled
    if not settings.DANDI_DOI_PUBLISH and event in ['publish', 'hide']:
        if 'event' in payload['data']['attributes']:
            del payload['data']['attributes']['event']
        logger.warning('DANDI_DOI_PUBLISH is not enabled. DOI %s will be updated as draft.', doi)

    update_url = f'{settings.DANDI_DOI_API_URL}/{doi}'
    try:
        response = requests.put(
            update_url,
            json=payload,
            auth=_get_auth(),
            headers=_get_headers(),
            timeout=_get_timeout(),
        )
        response.raise_for_status()
        return doi
    except requests.exceptions.HTTPError as e:
        error_details = f'Failed to update DOI {doi}'
        if e.response and hasattr(e.response, 'text'):
            error_details += f'\nResponse: {e.response.text}'
        error_details += f'\nPayload: {payload}'
        logger.exception(error_details)
        raise DataCiteAPIError(error_details) from e


@block_during_test
def delete_doi(doi: str) -> None:
    """
    Delete a draft DOI from the DataCite API.

    Args:
        doi: The DOI to delete.

    Raises:
        DataCiteNotConfiguredError: If the API is not configured.
        DataCiteAPIError: If the API request fails.
    """
    _validate_configuration()
    doi_url = f'{settings.DANDI_DOI_API_URL}/{doi}'

    try:
        # First, get DOI information to check its state
        response = requests.get(
            doi_url, auth=_get_auth(), headers=_get_headers(), timeout=_get_timeout()
        )
        response.raise_for_status()

        doi_data = response.json()
        # Get the state, defaulting to 'draft' if absent
        doi_state = doi_data.get('data', {}).get('attributes', {}).get('state', 'draft')

        if doi_state == 'draft':
            # Draft DOIs can be deleted
            delete_response = requests.delete(
                doi_url, auth=_get_auth(), headers=_get_headers(), timeout=_get_timeout()
            )
            delete_response.raise_for_status()
            logger.info('Successfully deleted draft DOI: %s', doi)
        else:
            logger.warning('Cannot delete non-draft DOI %s (state: %s)', doi, doi_state)

    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == requests.codes.not_found:
            logger.warning('Tried to get data for nonexistent DOI %s', doi)
            return
        logger.exception('Failed to delete DOI %s', doi)
        raise DataCiteAPIError(f'Failed to delete DOI {doi}') from e


@block_during_test
def hide_doi(doi: str) -> None:
    """
    Hide a findable DOI by converting it to a registered DOI.

    Args:
        doi: The DOI to hide.

    Raises:
        DataCiteNotConfiguredError: If the API is not configured.
        DataCitePublishNotEnabledError: If publish operations are not enabled.
        DataCiteAPIError: If the API request fails.
    """
    _validate_configuration()

    # Check if DANDI_DOI_PUBLISH is enabled for hiding
    if not settings.DANDI_DOI_PUBLISH:
        raise DataCitePublishNotEnabledError()

    doi_url = f'{settings.DANDI_DOI_API_URL}/{doi}'

    try:
        # First, get DOI information to check its state
        response = requests.get(
            doi_url, auth=_get_auth(), headers=_get_headers(), timeout=_get_timeout()
        )
        response.raise_for_status()

        doi_data = response.json()
        # Get the state, defaulting to 'draft' if absent
        doi_state = doi_data.get('data', {}).get('attributes', {}).get('state', 'draft')

        if doi_state == 'draft':
            logger.warning('Cannot hide draft DOI %s', doi)
            return

        # Create hide payload
        hide_payload = {'data': {'id': doi, 'type': 'dois', 'attributes': {'event': 'hide'}}}

        hide_response = requests.put(
            doi_url,
            json=hide_payload,
            auth=_get_auth(),
            headers=_get_headers(),
            timeout=_get_timeout(),
        )
        hide_response.raise_for_status()
        logger.info('Successfully hid findable DOI: %s', doi)

    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == requests.codes.not_found:
            logger.warning('Tried to get data for nonexistent DOI %s', doi)
            return
        logger.exception('Failed to hide DOI %s', doi)
        raise DataCiteAPIError(f'Failed to hide DOI {doi}') from e
