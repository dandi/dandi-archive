from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from dandischema.conf import get_instance_config
from django.conf import settings
import requests

from dandiapi.api.manifests import metalink_location

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

D3A_METALINK_MEDIA_TYPE = 'application/metalink4+xml'
DATACITE_CONTENT_TYPE = 'application/vnd.api+json'


def doi_configured() -> bool:
    return all(setting is not None for setting, _ in DANDI_DOI_SETTINGS)


def _add_d3a_related_identifier(request_body: dict, version: Version) -> None:
    related_identifier = {
        'relatedIdentifier': metalink_location(version),
        'relatedIdentifierType': 'URL',
        'relationType': 'HasMetadata',
        'relatedMetadataScheme': 'Metalink 4.0',
        'schemeURI': 'urn:ietf:params:xml:ns:metalink',
        'schemeType': D3A_METALINK_MEDIA_TYPE,
    }
    related_identifiers = request_body['data']['attributes'].setdefault('relatedIdentifiers', [])
    related_identifiers.append(related_identifier)


def _generate_doi_data(version: Version):
    from dandischema.datacite import to_datacite

    publish = settings.DANDI_DOI_PUBLISH
    # Use the DANDI test datacite instance as a placeholder if PREFIX isn't set
    prefix = settings.DANDI_DOI_API_PREFIX
    instance_name: str = get_instance_config().instance_name
    dandiset_id = version.dandiset.identifier
    version_id = version.version
    doi = f'{prefix}/{instance_name.lower()}.{dandiset_id}/{version_id}'
    metadata = version.metadata
    metadata['doi'] = doi
    request_body = to_datacite(metadata, publish=publish)
    _add_d3a_related_identifier(request_body, version)
    return (doi, request_body)


def _register_doi_d3a_media(doi: str, version: Version) -> None:
    requests.post(
        settings.DANDI_DOI_API_URL.rstrip('/') + '/' + doi + '/media',
        json={
            'data': {
                'type': 'media',
                'attributes': {
                    'mediaType': D3A_METALINK_MEDIA_TYPE,
                    'url': metalink_location(version),
                },
            }
        },
        headers={'Content-Type': DATACITE_CONTENT_TYPE},
        auth=requests.auth.HTTPBasicAuth(
            settings.DANDI_DOI_API_USER,
            settings.DANDI_DOI_API_PASSWORD,
        ),
        timeout=30,
    ).raise_for_status()


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
        try:
            _register_doi_d3a_media(doi, version)
        except requests.exceptions.RequestException:
            logger.exception('Failed to register D3A media for DOI %s', doi)
    return doi


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
