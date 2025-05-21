"""
DOI management interface for the DANDI Archive.

This module provides the public interface for DOI operations,
while the implementation details are in datacite.py.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from dandiapi.api.datacite import DataCiteClient

if TYPE_CHECKING:
    from dandiapi.api.models import Version

logger = logging.getLogger(__name__)


# Singleton instance
datacite_client = DataCiteClient()


def generate_doi_data(
    version: Version, version_doi: bool = True, event: str | None = None
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
    return datacite_client.generate_doi_data(version, version_doi, event)


def create_or_update_doi(datacite_payload: dict) -> str | None:
    """
    Create or update a DOI with the DataCite API.

    Args:
        datacite_payload: The DOI payload to send to DataCite.

    Returns:
        The DOI string on success, None on failure when not configured.

    Raises:
        requests.exceptions.HTTPError: If the API request fails.
    """
    return datacite_client.create_or_update_doi(datacite_payload)


def delete_or_hide_doi(doi: str) -> None:
    """
    Delete a draft DOI or hide a findable DOI depending on its state.

    This method first checks the DOI's state and then either deletes it (if it's a draft)
    or hides it (if it's findable). Hiding a DOI requires DANDI_DOI_PUBLISH to be enabled.

    Args:
        doi: The DOI to delete or hide.

    Raises:
        requests.exceptions.HTTPError: If the API request fails.
    """
    datacite_client.delete_or_hide_doi(doi)
