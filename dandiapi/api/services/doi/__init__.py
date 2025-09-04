"""
DataCite service functions.

This module provides service functions for interacting with the DataCite API,
refactored from the original datacite.py implementation and incorporating
DOI management functions from doi.py.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .datacite import create_doi, delete_doi, update_doi
from .utils import generate_doi_data

if TYPE_CHECKING:
    from dandiapi.api.models import Version

logger = logging.getLogger(__name__)


def create_dandiset_draft_doi(draft_version: Version) -> None:
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
    create_doi(dandiset_doi_payload)

    # Store the DOI in the draft version
    # TODO: Use update call instead
    draft_version.doi = dandiset_doi
    draft_version.save()


def update_draft_version_doi(draft_version: Version) -> None:
    """
    Update a Draft DOI for a dandiset with the latest metadata.

    This is called when a draft version's metadata is updated for a dandiset
    that has never been published.

    Args:
        draft_version: The draft version of the dandiset with updated metadata.
    """
    # Skip for dandisets that have published versions
    if draft_version.dandiset.versions.exclude(version='draft').exists():
        return

    if draft_version.doi is None:
        # TODO: Fix exception
        raise Exception('Should exist!')

    # Generate DOI payload with updated metadata
    dandiset_doi, dandiset_doi_payload = generate_doi_data(
        draft_version,
        version_doi=False,  # Generate a Dandiset DOI, not a Version DOI
        event=None,  # Keep as Draft DOI
    )

    # Update the DOI
    update_doi(dandiset_doi, dandiset_doi_payload)
    logger.info('Updated Draft DOI %s with new metadata', draft_version.doi)


def handle_publication_dois(version_id: int) -> None:
    """
    Create and update DOIs for a published version.

    Args:
        version_id: ID of the published version
    """
    from dandiapi.api.models import Version

    version = Version.objects.get(id=version_id)
    draft_version = version.dandiset.draft_version

    # Create Version DOI as Findable
    version_doi, version_doi_payload = generate_doi_data(version, version_doi=True, event='publish')

    # Update Dandiset DOI metadata and promote Findable (ok if already findable)
    dandiset_doi, dandiset_doi_payload = generate_doi_data(
        version,
        version_doi=False,
        event='publish',
    )

    # Create or update the DOIs
    # TODO(asmacdo): we need to try:except here, so dandiset doi doesn't block version doi
    create_or_update_doi(dandiset_doi_payload)
    create_or_update_doi(version_doi_payload)

    # Store the DOI values
    version.doi = version_doi
    draft_version.doi = dandiset_doi
    draft_version.save()
    version.save()
