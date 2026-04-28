from __future__ import annotations

import copy
from functools import wraps
import logging
import sys
from typing import TYPE_CHECKING

from dandischema.datacite import to_datacite
from django.conf import settings
import requests
from requests.adapters import HTTPAdapter, Retry
from requests.auth import HTTPBasicAuth

from .exceptions import (
    DataCiteAPIError,
    DataCiteNotConfiguredError,
    DataCitePublishNotEnabledError,
    DOIOperationNotPermittedError,
)

if TYPE_CHECKING:
    from dandiapi.api.models import Version
    from dandiapi.api.models.dandiset import Dandiset

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


def doi_configured() -> bool:
    """Check if the DOI client is properly configured."""
    return all(setting is not None for setting, _ in DANDI_DOI_SETTINGS)


def format_doi(dandiset_id: str, version_str: str | None = None) -> str:
    """Format a DOI string for a dandiset or version."""
    doi = f'{settings.DANDI_DOI_API_PREFIX}/dandi.{dandiset_id}'
    if version_str:
        doi += f'/{version_str}'

    return doi


def _validate_datacite_configuration(datacite_payload: dict) -> None:
    """Validate that DataCite API is properly configured."""
    if not doi_configured():
        raise DataCiteNotConfiguredError

    event = datacite_payload['data']['attributes'].get('event')
    if not settings.DANDI_DOI_PUBLISH and event in ['publish', 'hide']:
        raise DataCitePublishNotEnabledError


def get_doi_url(doi: str):
    """Return the URL for updating an existing DOI."""
    return f'{settings.DANDI_DOI_API_URL}/{doi}'


def generate_doi_data(
    dandiset: Dandiset, *, version: Version | None, publish: bool
) -> tuple[str, dict]:
    """Generate DOI data for a version or dandiset."""
    if version and not publish:
        raise DOIOperationNotPermittedError(message='Cannot generate non-publish version DOI')

    ver = version or dandiset.draft_version
    metadata = copy.deepcopy(ver.metadata)

    # Generate the appropriate DOI string
    if version:
        doi = format_doi(dandiset.identifier, version.version)
    else:
        # Dandiset DOI is the same as version url without version
        doi = format_doi(dandiset.identifier)
        metadata['url'] = metadata['url'].rsplit('/', 1)[0]
        metadata['version'] = dandiset.draft_version.metadata['id']

    metadata['doi'] = doi

    # Generate the datacite payload using dandi-schema
    datacite_payload = to_datacite(metadata, publish=publish)

    # TODO: DOI: Find better spot for this and/or break apart that function
    _validate_datacite_configuration(datacite_payload)

    return (doi, datacite_payload)


def raise_datacite_exception(desc: str, response: requests.Response, payload: dict):
    error_details = desc
    if response and hasattr(response, 'text'):
        error_details += f'\nResponse: {response.text}'
    error_details += f'\nPayload: {payload}'
    logger.exception(error_details)
    raise DataCiteAPIError(error_details)


def datacite_session():
    """Pre-configured session for all datacite requests."""
    session = requests.Session()
    session.auth = HTTPBasicAuth(settings.DANDI_DOI_API_USER, settings.DANDI_DOI_API_PASSWORD)
    session.headers = {'Accept': 'application/vnd.api+json'}
    # TODO: Timeout?

    retries = Retry(total=3, backoff_factor=0.1)
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    return session
