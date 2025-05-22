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


def _create_dandiset_draft_doi(draft_version: Version) -> None:
    """
    Create a Draft DOI for a dandiset.

    This is called during dandiset creation for public dandisets.
    For embargoed dandisets, no DOI is created until unembargo.

    Args:
        draft_version: The draft version of the dandiset.
    """
    # Generate a Draft DOI (event=None)
    dandiset_doi, dandiset_doi_payload = generate_doi_data(
        draft_version,
        version_doi=False,
        event=None,  # Draft DOI
    )

    # Create the DOI
    create_or_update_doi(dandiset_doi_payload)

    # Store the DOI in the draft version
    draft_version.doi = dandiset_doi
    draft_version.save()


def _handle_publication_dois(version_id: int) -> None:
    """
    Create and update DOIs for a published version.

    Args:
        version_id: ID of the published version
    """
    from dandiapi.api.models import Version

    version = Version.objects.get(id=version_id)
    draft_version = version.dandiset.draft_version

    # Check if this is the first publication (no prior DOI in draft version)
    # TODO(asmacdo) not true anymore, we need to check the db.
    # if draft_version.dandiset.versions.exclude(version='draft').exists():
    is_first_publication = draft_version.doi is None

    # Create Version DOI as Findable
    version_doi, version_doi_payload = generate_doi_data(
        version, version_doi=True, event='publish'
    )

    # Either create or update the Dandiset DOI based on whether it's the first publication
    if is_first_publication:
        # For first publication: generate Dandiset DOI and promote from Draft to Findable
        dandiset_doi, dandiset_doi_payload = generate_doi_data(
            version,
            version_doi=False,
            event='publish',  # Promote to Findable on first publication
        )
    else:
        # For subsequent publications: update the metadata but keep as Findable
        dandiset_doi, dandiset_doi_payload = generate_doi_data(
            version,
            version_doi=False,
            event='publish',  # Update existing Findable DOI
        )

    # Create or update the DOIs
    # TODO(asmacdo) we need to try:except here, so dandiset doi doesnt block version doi
    create_or_update_doi(dandiset_doi_payload)
    create_or_update_doi(version_doi_payload)

    # Store the DOI values
    version.doi = version_doi
    draft_version.doi = dandiset_doi

    # Save the values
    draft_version.save()
    version.save()
