"""
DataCite service functions.

This module provides service functions for interacting with the DataCite API,
refactored from the original datacite.py implementation and incorporating
DOI management functions from doi.py.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings

from dandiapi.api.services.doi.exceptions import (
    DOIOperationNotPermittedError,
    VersionDOIMissingError,
)

from .utils import datacite_session, generate_doi_data, get_doi_url, raise_datacite_exception

if TYPE_CHECKING:
    from dandiapi.api.models import Dandiset, Version

logger = logging.getLogger(__name__)


def _create_version_doi(version: Version) -> None:
    """Create a Findable DOI for a published dandiset version."""
    version_doi, datacite_payload = generate_doi_data(
        version.dandiset, version=version, publish=True
    )

    response = datacite_session().post(settings.DANDI_DOI_API_URL, json=datacite_payload)
    if not response.ok:
        raise_datacite_exception(
            desc=f'Failed to create findable DOI {version_doi}',
            response=response,
            payload=datacite_payload,
        )

    logger.info('Created findable DOI %s', version_doi)


def create_dandiset_doi(dandiset: Dandiset) -> None:
    """
    Create a Draft DOI for a dandiset.

    This is called during dandiset creation for public dandisets.
    For embargoed dandisets, no DOI is created until unembargo.
    """
    dandiset_doi, datacite_payload = generate_doi_data(dandiset, version=None, publish=False)
    response = datacite_session().post(settings.DANDI_DOI_API_URL, json=datacite_payload)
    if not response.ok:
        raise_datacite_exception(
            desc=f'Failed to create DOI {dandiset_doi}',
            response=response,
            payload=datacite_payload,
        )

    logger.info('Created Draft DOI %s with new metadata', dandiset_doi)


def update_dandiset_doi(dandiset: Dandiset, *, publish: bool = False) -> None:
    """
    Update a Draft DOI for a dandiset with the latest metadata.

    This is called when a draft version's metadata is updated.
    """
    # Don't continue for dandisets with published versions, unless this is a publish event
    if not publish and dandiset.most_recent_published_version is not None:
        raise DOIOperationNotPermittedError(
            message='DOI update for dandiset with published versions not allowed'
        )

    # Don't continue for embargoed dandisets
    if dandiset.embargoed:
        raise DOIOperationNotPermittedError(
            message='Cannot perform DOI operations on embargoed dandisets'
        )

    # TODO: DOI: Remove once DOI is required in all versions
    if dandiset.draft_version.doi is None:
        raise VersionDOIMissingError

    dandiset_doi, datacite_payload = generate_doi_data(dandiset, version=None, publish=publish)
    response = datacite_session().put(get_doi_url(dandiset_doi), json=datacite_payload)
    if not response.ok:
        raise_datacite_exception(
            desc=f'Failed to update DOI {dandiset_doi}', response=response, payload=datacite_payload
        )

    logger.info('Updated Draft DOI %s with new metadata', dandiset_doi)


def delete_dandiset_doi(doi: str):
    """
    Delete the draft DOI of a dandiset.

    This function only accepts the raw DOI string, as the
    dandiset itself will be deleted by the time it's called.
    """
    response = datacite_session().delete(get_doi_url(doi))
    if not response.ok:
        raise_datacite_exception(
            desc=f'Failed to delete draft DOI {doi}', response=response, payload={}
        )

    logger.info('Successfully deleted draft DOI: %s', doi)


def create_published_version_doi(version: Version) -> None:
    """
    Create a DOI for a published version.

    As a side effect, this also updates the DOI of the version's
    dandiset to match this version's DOI metadata.
    """
    _create_version_doi(version)
    update_dandiset_doi(version.dandiset, publish=True)


def hide_published_version_doi(version: Version):
    if version.version == 'draft':
        raise DOIOperationNotPermittedError(message='Cannot hide a draft dandiset DOI')

    # TODO: DOI: Remove once DOI is required in all versions
    doi = version.doi
    if doi is None:
        raise VersionDOIMissingError

    payload = {'data': {'id': doi, 'type': 'dois', 'attributes': {'event': 'hide'}}}
    response = datacite_session().put(get_doi_url(doi), json=payload)
    if not response.ok:
        raise_datacite_exception(
            desc=f'Failed to hide findable DOI {doi}', response=response, payload=payload
        )

    logger.info('Successfully hid findable DOI: %s', doi)
