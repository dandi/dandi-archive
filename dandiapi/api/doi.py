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
    dandiset_doi, dandiset_doi_payload = datacite_client.generate_doi_data(
        draft_version,
        version_doi=False,
        event=None,  # Draft DOI
    )

    # Create the DOI
    datacite_client.create_or_update_doi(dandiset_doi_payload)

    # Store the DOI in the draft version
    draft_version.doi = dandiset_doi
    draft_version.save()


def _update_draft_version_doi(draft_version: Version) -> None:
    """
    Update or create a Draft DOI for a dandiset with the latest metadata.

    This is called when a draft version's metadata is updated for a dandiset
    that has never been published.

    Args:
        draft_version: The draft version of the dandiset with updated metadata.
    """
    # Skip for dandisets that have published versions
    if draft_version.dandiset.versions.exclude(version='draft').exists():
        return

    # Generate DOI payload with updated metadata
    dandiset_doi, dandiset_doi_payload = datacite_client.generate_doi_data(
        draft_version,
        version_doi=False,  # Generate a Dandiset DOI, not a Version DOI
        event=None,  # Keep as Draft DOI
    )

    # Create or update the DOI
    datacite_client.create_or_update_doi(dandiset_doi_payload)

    # If the version doesn't have a DOI yet, store it
    if draft_version.doi is None:
        draft_version.doi = dandiset_doi
        draft_version.save()
        logger.info('Created new Draft DOI %s', dandiset_doi)
    else:
        logger.info('Updated Draft DOI %s with new metadata', draft_version.doi)


def _handle_publication_dois(version_id: int) -> None:
    """
    Create and update DOIs for a published version.

    Args:
        version_id: ID of the published version
    """
    from dandiapi.api.models import Version

    version = Version.objects.get(id=version_id)
    draft_version = version.dandiset.draft_version

    # Create Version DOI as Findable
    version_doi, version_doi_payload = datacite_client.generate_doi_data(
        version, version_doi=True, event='publish'
    )

    # Update Dandiset DOI metadata and promote Findable (ok if already findable)
    dandiset_doi, dandiset_doi_payload = datacite_client.generate_doi_data(
        version,
        version_doi=False,
        event='publish',
    )

    # Create or update the DOIs
    # TODO(asmacdo): we need to try:except here, so dandiset doi doesn't block version doi
    datacite_client.create_or_update_doi(dandiset_doi_payload)
    datacite_client.create_or_update_doi(version_doi_payload)

    # Store the DOI values
    version.doi = version_doi
    draft_version.doi = dandiset_doi
    draft_version.save()
    version.save()
