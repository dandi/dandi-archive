from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, Optional, Tuple

from django.conf import settings
import requests

if TYPE_CHECKING:
    from dandiapi.api.models import Version

# All of the required DOI configuration settings
DANDI_DOI_SETTINGS = [
    (settings.DANDI_DOI_API_URL, 'DANDI_DOI_API_URL'),
    (settings.DANDI_DOI_API_USER, 'DANDI_DOI_API_USER'),
    (settings.DANDI_DOI_API_PASSWORD, 'DANDI_DOI_API_PASSWORD'),
    (settings.DANDI_DOI_API_PREFIX, 'DANDI_DOI_API_PREFIX'),
]

# Whether DOI publishing is enabled
DOI_PUBLISH_ENABLED = settings.DANDI_DOI_PUBLISH

logger = logging.getLogger(__name__)


class DataCiteClient:
    """Client for interacting with the DataCite API."""

    def __init__(self):
        self.api_url = settings.DANDI_DOI_API_URL
        self.api_user = settings.DANDI_DOI_API_USER
        self.api_password = settings.DANDI_DOI_API_PASSWORD
        self.api_prefix = settings.DANDI_DOI_API_PREFIX or '10.80507'
        self.auth = requests.auth.HTTPBasicAuth(self.api_user, self.api_password)
        self.headers = {'Accept': 'application/vnd.api+json'}
        self.timeout = 30

    def is_configured(self) -> bool:
        """Check if the DOI client is properly configured."""
        return all(setting is not None for setting, _ in DANDI_DOI_SETTINGS)

    def format_doi(self, dandiset_id: str, version_id: Optional[str] = None) -> str:
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
            return f'{self.api_prefix}/dandi.{dandiset_id}/{version_id}'
        return f'{self.api_prefix}/dandi.{dandiset_id}'

    def generate_doi_data(
        self, 
        version: Version, 
        version_doi: bool = True, 
        event: Optional[str] = None
    ) -> Tuple[str, Dict]:
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
        from dandischema.datacite import to_datacite

        # If DOI_PUBLISH_ENABLED is not True, we should only create draft DOIs
        if not DOI_PUBLISH_ENABLED and event in ["publish", "hide"]:
            logger.warning(
                "DANDI_DOI_PUBLISH is not enabled. Requested event '%s' but creating draft DOI instead.",
                event
            )
            event = None  # Force event to None (draft DOI)

        dandiset_id = version.dandiset.identifier
        version_id = version.version
        metadata = version.metadata.copy()  # Create a copy to avoid modifying the original

        # Generate the appropriate DOI string
        if version_doi:
            doi = self.format_doi(dandiset_id, version_id)
        else:
            doi = self.format_doi(dandiset_id)
            # Dandiset DOI is the same as version url without version
            metadata['url'] = metadata['url'].rsplit('/', 1)[0]
        
        metadata['doi'] = doi
        
        # Generate the datacite payload with the appropriate event
        datacite_payload = to_datacite(metadata, event=event)
        
        return (doi, datacite_payload)

    def create_or_update_doi(self, datacite_payload: Dict) -> Optional[str]:
        """
        Create or update a DOI with the DataCite API.
        
        Args:
            datacite_payload: The DOI payload to send to DataCite.
            
        Returns:
            The DOI string on success, None on failure when not configured.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        if not self.is_configured():
            logger.warning("DOI NOT CONFIGURED!!!")
            return None

        doi = datacite_payload["data"]["attributes"]["doi"]
        
        # Check if we're trying to create a non-draft DOI when it's not allowed
        event = datacite_payload["data"]["attributes"].get("event")
        if not DOI_PUBLISH_ENABLED and event in ["publish", "hide"]:
            logger.warning(
                "DANDI_DOI_PUBLISH is not enabled. Skipping create/update with event '%s' for DOI %s.",
                event, doi
            )
            # Return the DOI string even though we didn't create it
            # This prevents errors in the calling code
            return doi

        try:
            response = requests.post(
                self.api_url, 
                json=datacite_payload, 
                auth=self.auth, 
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return doi
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 422:
                # Retry with PUT if DOI already exists
                update_url = f"{self.api_url}/{doi}"
                try:
                    update_response = requests.put(
                        update_url, 
                        json=datacite_payload, 
                        auth=self.auth,
                        headers=self.headers,
                        timeout=self.timeout
                    )
                    update_response.raise_for_status()
                    return doi
                except Exception:
                    logger.exception('Failed to update existing DOI %s', doi)
                    logger.exception(datacite_payload)
                    if e.response:
                        logger.exception(e.response.text)
                    raise
            else:
                logger.exception('Failed to create DOI %s', doi)
                logger.exception(datacite_payload)
                if e.response:
                    logger.exception(e.response.text)
                raise

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
        # If DOI isn't configured, skip the API call
        if not self.is_configured():
            logger.warning(f"DOI NOT CONFIGURED!!! Skipping operations for {doi}")
            return

        doi_url = f"{self.api_url}/{doi}"

        try:
            # First, get DOI information to check its state
            response = requests.get(
                doi_url, 
                auth=self.auth,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            doi_data = response.json()
            # Get the state, defaulting to 'draft' if absent
            doi_state = doi_data.get('data', {}).get('attributes', {}).get('state', 'draft')
            
            if doi_state == 'draft':
                # Draft DOIs can be deleted
                delete_response = requests.delete(
                    doi_url, 
                    auth=self.auth,
                    headers=self.headers,
                    timeout=self.timeout
                )
                delete_response.raise_for_status()
                logger.info(f"Successfully deleted draft DOI: {doi}")
            else:
                # Findable DOIs must be hidden
                # Check if DANDI_DOI_PUBLISH is enabled for hiding
                if not DOI_PUBLISH_ENABLED:
                    logger.warning(
                        f"DANDI_DOI_PUBLISH is not enabled. Cannot hide findable DOI {doi}."
                    )
                    return
                
                # Create hide payload
                hide_payload = {
                    "data": {
                        "id": doi,
                        "type": "dois",
                        "attributes": {
                            "event": "hide"
                        }
                    }
                }
                
                hide_response = requests.put(
                    doi_url,
                    json=hide_payload, 
                    auth=self.auth,
                    headers=self.headers,
                    timeout=self.timeout
                )
                hide_response.raise_for_status()
                logger.info(f"Successfully hid findable DOI: {doi}")
                
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == requests.codes.not_found:
                logger.warning(f'Tried to get data for nonexistent DOI {doi}')
                return
            logger.exception(f'Failed to delete or hide DOI {doi}')
            raise

    def delete_doi(self, doi: str) -> None:
        """
        Delete a DOI if it's in draft state.
        
        Args:
            doi: The DOI to delete.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        self.delete_or_hide_doi(doi)

    def hide_doi(self, doi: str) -> None:
        """
        Convert a Findable DOI to a Registered DOI.
        
        This is used when deleting a published dandiset or version.
        
        Args:
            doi: The DOI to hide.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        self.delete_or_hide_doi(doi)


# Singleton instance
datacite_client = DataCiteClient()


# Functional interface to maintain compatibility
def doi_configured() -> bool:
    """Check if DOI is configured."""
    return datacite_client.is_configured()


def generate_doi_data(
    version: Version, 
    version_doi: bool = True, 
    event: Optional[str] = None
) -> Tuple[str, Dict]:
    """Generate DOI data for a version or dandiset."""
    return datacite_client.generate_doi_data(version, version_doi, event)


def create_or_update_doi(datacite_payload: Dict) -> Optional[str]:
    """Create or update a DOI with the DataCite API."""
    return datacite_client.create_or_update_doi(datacite_payload)


def delete_doi(doi: str) -> None:
    """Delete a DOI if it's in draft state."""
    datacite_client.delete_doi(doi)


def hide_doi(doi: str) -> None:
    """Convert a Findable DOI to a Registered DOI."""
    datacite_client.hide_doi(doi)