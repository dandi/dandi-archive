from __future__ import annotations

import copy
from functools import wraps
import logging
import sys
from typing import TYPE_CHECKING

from django.conf import settings

from .exceptions import (
    DataCiteAPIError,
    DataCiteNotConfiguredError,
    DataCitePublishNotEnabledError,
)

if TYPE_CHECKING:
    import requests

    from dandiapi.api.models import Version

logger = logging.getLogger(__name__)

# All of the required DOI configuration settings
# Cannot be in doi.py to avoid circular imports
DANDI_DOI_SETTINGS = [
    (settings.DANDI_DOI_API_URL, 'DANDI_DOI_API_URL'),
    (settings.DANDI_DOI_API_USER, 'DANDI_DOI_API_USER'),
    (settings.DANDI_DOI_API_PASSWORD, 'DANDI_DOI_API_PASSWORD'),
    (settings.DANDI_DOI_API_PREFIX, 'DANDI_DOI_API_PREFIX'),
]


def block_during_test(fn):
    """Datacite API should not be called during tests."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'pytest' in sys.modules:
            raise RuntimeError(f'DOI calls to {fn.__name__} blocked during test.')
        return fn(*args, **kwargs)

    return wrapper


def _is_configured() -> bool:
    """Check if the DOI client is properly configured."""
    return all(setting is not None for setting, _ in DANDI_DOI_SETTINGS)


def format_doi(dandiset_id: str, version_id: str | None = None) -> str:
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
        return f'{settings.DANDI_DOI_API_PREFIX}/dandi.{dandiset_id}/{version_id}'
    return f'{settings.DANDI_DOI_API_PREFIX}/dandi.{dandiset_id}'


def generate_doi_data(
    version: Version, *, version_doi: bool = True, event: str | None = None
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
        doi = format_doi(dandiset_id, version_id)
    else:
        # Dandiset DOI is the same as version url without version
        doi = format_doi(dandiset_id)
        metadata['url'] = metadata['url'].rsplit('/', 1)[0]
        metadata['version'] = version.dandiset.draft_version.metadata['id']

    metadata['doi'] = doi

    # Generate the datacite payload with the appropriate publish status
    # Convert event to publish boolean for the to_datacite function
    publish = event == 'publish'
    datacite_payload = to_datacite(metadata, publish=publish)

    return (doi, datacite_payload)


def _validate_configuration() -> None:
    """Validate that DataCite API is properly configured."""
    if not _is_configured():
        raise DataCiteNotConfiguredError


def _validate_publish_enabled(event: str | None = None) -> None:
    """Validate that publish operations are enabled if needed."""
    if not settings.DANDI_DOI_PUBLISH and event in ['publish', 'hide']:
        raise DataCitePublishNotEnabledError


def raise_datacite_exception(desc: str, response: requests.Response, payload: dict):
    error_details = desc
    if response and hasattr(response, 'text'):
        error_details += f'\nResponse: {response.text}'
    error_details += f'\nPayload: {payload}'
    logger.exception(error_details)
    raise DataCiteAPIError(error_details)
