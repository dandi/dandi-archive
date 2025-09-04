"""
DataCite API client implementation.

This module provides the implementation details for interacting with the DataCite API.
The public interface is exposed through doi.py.
"""

from __future__ import annotations

import copy
from functools import wraps
import logging
import sys
from typing import TYPE_CHECKING

from django.conf import settings
import requests

if TYPE_CHECKING:
    from dandiapi.api.models import Version

# All of the required DOI configuration settings
# Cannot be in doi.py to avoid circular imports
DANDI_DOI_SETTINGS = [
    (settings.DANDI_DOI_API_URL, 'DANDI_DOI_API_URL'),
    (settings.DANDI_DOI_API_USER, 'DANDI_DOI_API_USER'),
    (settings.DANDI_DOI_API_PASSWORD, 'DANDI_DOI_API_PASSWORD'),
    (settings.DANDI_DOI_API_PREFIX, 'DANDI_DOI_API_PREFIX'),
]

logger = logging.getLogger(__name__)


def block_during_test(fn):
    """Datacite API should not be called."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'pytest' in sys.modules:
            raise RuntimeError(f'DOI calls to {fn.__name__} blocked during test.')
        return fn(*args, **kwargs)

    return wrapper


class DataCiteClient:
    """Client for interacting with the DataCite API."""

    def __init__(self):
        self.api_url = settings.DANDI_DOI_API_URL
        self.api_user = settings.DANDI_DOI_API_USER
        self.api_password = settings.DANDI_DOI_API_PASSWORD
        self.api_prefix = settings.DANDI_DOI_API_PREFIX
        self.auth = requests.auth.HTTPBasicAuth(self.api_user, self.api_password)
        self.headers = {'Accept': 'application/vnd.api+json'}
        self.timeout = 30

    def is_configured(self) -> bool:
        """Check if the DOI client is properly configured."""
        return all(setting is not None for setting, _ in DANDI_DOI_SETTINGS)

    def format_doi(self, dandiset_id: str, version_id: str | None = None) -> str:
        """
        Format a DOI string for a dandiset or version.

        Args:
            dandiset_id: The dandiset identifier.
            version_id: Optional version identifier. If provided, creates a Version DOI.
                        If omitted, creates a Dandiset DOI.

        Returns:
            Formatted DOI string.
        """
        if version_id:
            # TODO(asmaco): replace "dandi" with non-hardcoded ID_PATTERN
            # https://github.com/dandi/dandi-schema/pull/294/files#diff-43c9cc813638d87fd33e527a7baccb2fd7dff85595a7e686bfaf61f0409bd403R47
            return f'{self.api_prefix}/dandi.{dandiset_id}/{version_id}'
        return f'{self.api_prefix}/dandi.{dandiset_id}'

    def generate_doi_data(
        self, version: Version, *, version_doi: bool = True, event: str | None = None
    ) -> tuple[str, dict]:
        """
        Generate DOI data for a version or dandiset.

        Args:
            version: Version object containing metadata.
            version_doi: If True, generate a Version DOI, otherwise generate a Dandiset DOI.
            event: The DOI event type.
                - None: Creates a Draft DOI.
                - "publish": Creates or promotes to a Findable DOI.
                - "hide": Converts to a Registered DOI.

        Returns:
            Tuple of (doi_string, datacite_payload)
        """
        # TODO(asmacdo): if not datacite configured make sure we dont save any dois to model
        from dandischema.datacite import to_datacite

        dandiset_id = version.dandiset.identifier
        version_id = version.version
        metadata = copy.deepcopy(version.metadata)

        # Generate the appropriate DOI string
        if version_doi:
            doi = self.format_doi(dandiset_id, version_id)
        else:
            doi = self.format_doi(dandiset_id)
            # Dandiset DOI is the same as version url without version
            metadata['url'] = metadata['url'].rsplit('/', 1)[0]
            metadata['version'] = version.dandiset.draft_version.metadata['id']

        metadata['doi'] = doi

        # Generate the datacite payload with the appropriate event
        datacite_payload = to_datacite(metadata, event=event)

        return (doi, datacite_payload)

    @block_during_test
    def create_or_update_doi(self, original_datacite_payload: dict) -> str | None:
        """
        Create or update a DOI with the DataCite API.

        Args:
            datacite_payload: The DOI payload to send to DataCite.

        Returns:
            The DOI string on success, None on failure when not configured.

        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        datacite_payload = copy.deepcopy(original_datacite_payload)
        doi = datacite_payload['data']['attributes']['doi']

        if not self.is_configured():
            logger.warning('DOI API not configured. Skipping operations for %s', doi)
            return None

        # Check if we're trying to create a non-draft DOI when it's not allowed
        event = datacite_payload['data']['attributes'].get('event')
        if not settings.DANDI_DOI_PUBLISH and event in ['publish', 'hide']:
            # Remove the event to make it a draft DOI
            if 'event' in datacite_payload['data']['attributes']:
                del datacite_payload['data']['attributes']['event']

            logger.warning(
                'DANDI_DOI_PUBLISH is not enabled. DOI %s will be created as draft.', doi
            )

        try:
            response = requests.post(
                self.api_url,
                json=datacite_payload,
                auth=self.auth,
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            # Return early on success
            return doi  # noqa: TRY300
        except requests.exceptions.HTTPError as e:
            # HTTP 422 status code means DOI already exists
            already_exists_code = 422
            if e.response is not None and e.response.status_code == already_exists_code:
                # Retry with PUT if DOI already exists
                update_url = f'{self.api_url}/{doi}'
                try:
                    update_response = requests.put(
                        update_url,
                        json=datacite_payload,
                        auth=self.auth,
                        headers=self.headers,
                        timeout=self.timeout,
                    )
                    update_response.raise_for_status()
                    return doi  # noqa: TRY300
                except Exception:
                    error_details = f'Failed to update existing DOI {doi}'
                    if e.response and hasattr(e.response, 'text'):
                        error_details += f'\nResponse: {e.response.text}'
                    error_details += f'\nPayload: {datacite_payload}'
                    logger.exception(error_details)
                    raise
            else:
                error_details = f'Failed to create DOI {doi}'
                if e.response and hasattr(e.response, 'text'):
                    error_details += f'\nResponse: {e.response.text}'
                error_details += f'\nPayload: {datacite_payload}'
                logger.exception(error_details)
                raise

    @block_during_test
    def delete_or_hide_doi(self, doi: str) -> None:
        """
        Delete a draft DOI or hide a findable DOI depending on its state.

        This method first checks the DOI's state and then either deletes it (if it's a draft)
        or hides it (if it's findable). Hiding a DOI requires DANDI_DOI_PUBLISH to be enabled.

        Args:
            doi: The DOI to delete or hide.

        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        if not self.is_configured():
            logger.warning('DOI API not configured. Skipping operations for %s', doi)
            return

        doi_url = f'{self.api_url}/{doi}'

        try:
            # First, get DOI information to check its state
            response = requests.get(
                doi_url, auth=self.auth, headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()

            doi_data = response.json()
            # Get the state, defaulting to 'draft' if absent
            doi_state = doi_data.get('data', {}).get('attributes', {}).get('state', 'draft')

            if doi_state == 'draft':
                # Draft DOIs can be deleted
                delete_response = requests.delete(
                    doi_url, auth=self.auth, headers=self.headers, timeout=self.timeout
                )
                delete_response.raise_for_status()
                logger.info('Successfully deleted draft DOI: %s', doi)
            else:
                # Findable DOIs must be hidden
                # Check if DANDI_DOI_PUBLISH is enabled for hiding
                if not settings.DANDI_DOI_PUBLISH:
                    logger.warning(
                        'DANDI_DOI_PUBLISH is not enabled. DOI %s will remain findable.', doi
                    )
                    return

                # Create hide payload
                hide_payload = {
                    'data': {'id': doi, 'type': 'dois', 'attributes': {'event': 'hide'}}
                }

                hide_response = requests.put(
                    doi_url,
                    json=hide_payload,
                    auth=self.auth,
                    headers=self.headers,
                    timeout=self.timeout,
                )
                hide_response.raise_for_status()
                logger.info('Successfully hid findable DOI: %s', doi)

        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == requests.codes.not_found:
                logger.warning('Tried to get data for nonexistent DOI %s', doi)
                return
            logger.exception('Failed to delete or hide DOI %s', doi)
            raise
