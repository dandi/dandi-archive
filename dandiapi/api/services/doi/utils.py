from __future__ import annotations

from contextlib import contextmanager
import copy
import logging
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
    from collections.abc import Generator

    from dandiapi.api.models import Version
    from dandiapi.api.models.dandiset import Dandiset

logger = logging.getLogger(__name__)

# All of the required DOI configuration settings
DANDI_DOI_SETTINGS = [
    (settings.DANDI_DOI_API_URL, 'DANDI_DOI_API_URL'),
    (settings.DANDI_DOI_API_USER, 'DANDI_DOI_API_USER'),
    (settings.DANDI_DOI_API_PASSWORD, 'DANDI_DOI_API_PASSWORD'),
    (settings.DANDI_DOI_API_PREFIX, 'DANDI_DOI_API_PREFIX'),
]

# Default timeout for DataCite API calls: (connect, read) in seconds
DATACITE_TIMEOUT = (5, 30)


def doi_configured() -> bool:
    """Check if the DOI client is properly configured."""
    return all(setting is not None for setting, _ in DANDI_DOI_SETTINGS)


def format_doi(dandiset_id: str, version_str: str | None = None) -> str:
    """Format a DOI string for a dandiset or version, using the instance name from config."""
    from dandischema.conf import get_instance_config

    instance_name = get_instance_config().instance_name.lower()
    doi = f'{settings.DANDI_DOI_API_PREFIX}/{instance_name}.{dandiset_id}'
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

    # Pass concept_doi for IsVersionOf relation when generating version DOI payloads
    concept_doi = dandiset.concept_doi if version else None
    try:
        datacite_payload = to_datacite(metadata, publish=publish, concept_doi=concept_doi)
    except TypeError as e:
        if 'concept_doi' in str(e):
            # Fallback for dandischema versions that don't support concept_doi parameter
            datacite_payload = to_datacite(metadata, publish=publish)
        else:
            raise

    _validate_datacite_configuration(datacite_payload)

    return (doi, datacite_payload)


def raise_datacite_exception(desc: str, response: requests.Response, payload: dict):
    error_details = desc
    if response and hasattr(response, 'text'):
        error_details += f'\nResponse: {response.text}'
    error_details += f'\nPayload: {payload}'
    logger.error(error_details)
    raise DataCiteAPIError(error_details)


@contextmanager
def datacite_session() -> Generator[requests.Session]:
    """Pre-configured session for all DataCite requests. Use as context manager."""
    session = requests.Session()
    session.auth = HTTPBasicAuth(settings.DANDI_DOI_API_USER, settings.DANDI_DOI_API_PASSWORD)
    session.headers.update(
        {
            'Accept': 'application/vnd.api+json',
            'Content-Type': 'application/vnd.api+json',
        }
    )

    retries = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET', 'PUT', 'POST', 'DELETE'],
    )
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        yield session
    finally:
        session.close()
