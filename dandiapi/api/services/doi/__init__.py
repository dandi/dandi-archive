"""
DataCite service functions.

This module provides service functions for interacting with the DataCite API.
All HTTP calls use datacite_session() as a context manager with timeouts and retry.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings

from dandiapi.api.services.doi.exceptions import (
    DOIOperationNotPermittedError,
    VersionDOIMissingError,
)

from .utils import (
    DATACITE_TIMEOUT,
    datacite_session,
    generate_doi_data,
    get_doi_url,
    raise_datacite_exception,
)

if TYPE_CHECKING:
    from dandiapi.api.models import Dandiset, Version

logger = logging.getLogger(__name__)


def _create_version_doi(version: Version) -> None:
    """Create a Findable DOI for a published dandiset version."""
    version_doi, datacite_payload = generate_doi_data(
        version.dandiset, version=version, publish=True
    )

    with datacite_session() as session:
        response = session.post(
            settings.DANDI_DOI_API_URL, json=datacite_payload, timeout=DATACITE_TIMEOUT
        )
    if not response.ok:
        raise_datacite_exception(
            desc=f'Failed to create findable DOI {version_doi}',
            response=response,
            payload=datacite_payload,
        )

    logger.info('Created findable DOI %s', version_doi)


def create_dandiset_doi(dandiset: Dandiset) -> None:
    """
    Create a Draft DOI for a dandiset (concept DOI).

    Called during dandiset creation for public dandisets.
    For embargoed dandisets, no DOI is created until unembargo.
    """
    dandiset_doi, datacite_payload = generate_doi_data(dandiset, version=None, publish=False)

    with datacite_session() as session:
        response = session.post(
            settings.DANDI_DOI_API_URL, json=datacite_payload, timeout=DATACITE_TIMEOUT
        )
    if not response.ok:
        raise_datacite_exception(
            desc=f'Failed to create DOI {dandiset_doi}',
            response=response,
            payload=datacite_payload,
        )

    logger.info('Created Draft concept DOI %s', dandiset_doi)


def update_dandiset_doi(dandiset: Dandiset, *, publish: bool = False) -> None:
    """
    Update a concept DOI for a dandiset with the latest metadata.

    When publish=True, promotes the concept DOI from Draft to Findable.
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

    with datacite_session() as session:
        response = session.put(
            get_doi_url(dandiset_doi), json=datacite_payload, timeout=DATACITE_TIMEOUT
        )
    if not response.ok:
        raise_datacite_exception(
            desc=f'Failed to update DOI {dandiset_doi}',
            response=response,
            payload=datacite_payload,
        )

    logger.info('Updated concept DOI %s (publish=%s)', dandiset_doi, publish)


def delete_dandiset_doi(doi: str) -> None:
    """
    Delete the Draft concept DOI of a dandiset.

    Only Draft DOIs can be deleted. Findable DOIs must be hidden instead.
    """
    with datacite_session() as session:
        response = session.delete(get_doi_url(doi), timeout=DATACITE_TIMEOUT)
    if not response.ok:
        raise_datacite_exception(
            desc=f'Failed to delete draft DOI {doi}', response=response, payload={}
        )

    logger.info('Deleted draft concept DOI: %s', doi)


def create_published_version_doi(version: Version) -> None:
    """
    Create a Findable DOI for a published version.

    Also promotes/updates the concept DOI to Findable with HasVersion link.
    """
    _create_version_doi(version)
    update_dandiset_doi(version.dandiset, publish=True)


def hide_published_version_doi(version: Version) -> None:
    """Hide (retract) a Findable version DOI by transitioning to Registered state."""
    if version.version == 'draft':
        raise DOIOperationNotPermittedError(message='Cannot hide a draft dandiset DOI')

    doi = version.doi
    if doi is None:
        raise VersionDOIMissingError

    payload = {'data': {'id': doi, 'type': 'dois', 'attributes': {'event': 'hide'}}}

    with datacite_session() as session:
        response = session.put(get_doi_url(doi), json=payload, timeout=DATACITE_TIMEOUT)
    if not response.ok:
        raise_datacite_exception(
            desc=f'Failed to hide findable DOI {doi}', response=response, payload=payload
        )

    logger.info('Hid findable DOI: %s', doi)
