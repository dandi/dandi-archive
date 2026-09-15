from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from dandischema.conf import get_instance_config
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

logger = logging.getLogger(__name__)


def doi_configured() -> bool:
    return all(setting is not None for setting, _ in DANDI_DOI_SETTINGS)


def doi_for_version(version: Version) -> str:
    """Compute the DOI a Version has (or would have) at DataCite.

    Purely deterministic -- no API call, no side effects. Because it is
    deterministic, a Version whose ``doi`` column is NULL may nonetheless
    already have this DOI registered at DataCite (minted at publish time,
    then not persisted); see ``get_doi``.
    """
    # Use the DANDI test datacite instance as a placeholder if PREFIX isn't set
    prefix = settings.DANDI_DOI_API_PREFIX
    instance_name: str = get_instance_config().instance_name
    dandiset_id = version.dandiset.identifier
    version_id = version.version
    return f'{prefix}/{instance_name.lower()}.{dandiset_id}/{version_id}'


def _generate_doi_data(version: Version):
    from dandischema.datacite import to_datacite

    publish = settings.DANDI_DOI_PUBLISH
    doi = doi_for_version(version)
    metadata = version.metadata
    metadata['doi'] = doi
    return (doi, to_datacite(metadata, publish=publish))


def create_doi(version: Version) -> str:
    doi, request_body = _generate_doi_data(version)
    # If DOI isn't configured, skip the API call
    if doi_configured():
        try:
            requests.post(
                settings.DANDI_DOI_API_URL,
                json=request_body,
                auth=requests.auth.HTTPBasicAuth(
                    settings.DANDI_DOI_API_USER,
                    settings.DANDI_DOI_API_PASSWORD,
                ),
                timeout=30,
            ).raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.exception('Failed to create DOI %s', doi)
            logger.exception(request_body)
            if e.response:
                logger.exception(e.response.text)
            raise
    return doi


def get_doi(doi: str) -> dict | None:
    """Fetch a DOI's ``attributes`` from DataCite; None if it isn't registered.

    Returns None (without an API call) when DOI minting isn't configured.
    """
    if not doi_configured():
        logger.debug('Skipping DOI lookup for %s since not configured', doi)
        return None

    doi_url = settings.DANDI_DOI_API_URL.rstrip('/') + '/' + doi
    try:
        r = requests.get(
            doi_url,
            auth=requests.auth.HTTPBasicAuth(
                settings.DANDI_DOI_API_USER,
                settings.DANDI_DOI_API_PASSWORD,
            ),
            headers={'Accept': 'application/vnd.api+json'},
            timeout=30,
        )
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == requests.codes.not_found:
            return None
        logger.exception('Failed to fetch data for DOI %s', doi)
        raise
    return r.json()['data']['attributes']


def delete_doi(doi: str) -> None:
    # If DOI isn't configured, skip the API call
    if doi_configured():
        doi_url = settings.DANDI_DOI_API_URL.rstrip('/') + '/' + doi
        with requests.Session() as s:
            s.auth = (settings.DANDI_DOI_API_USER, settings.DANDI_DOI_API_PASSWORD)
            try:
                r = s.get(doi_url, headers={'Accept': 'application/vnd.api+json'})
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code == requests.codes.not_found:
                    logger.warning('Tried to get data for nonexistent DOI %s', doi)
                    return
                logger.exception('Failed to fetch data for DOI %s', doi)
                raise
            if r.json()['data']['attributes']['state'] == 'draft':
                try:
                    s.delete(doi_url).raise_for_status()
                except requests.exceptions.HTTPError:
                    logger.exception('Failed to delete DOI %s', doi)
                    raise
    else:
        logger.debug('Skipping DOI deletion for %s since not configured', doi)
