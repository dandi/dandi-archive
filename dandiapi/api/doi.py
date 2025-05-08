from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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
    return any(setting is not None for setting, _ in DANDI_DOI_SETTINGS)


# TODO(asmacdo) findable dois
# def _generate_doi_data(version: Version, event: str):
def generate_doi_data(version: Version, version_doi=True):
    from dandischema.datacite import to_datacite

    publish = settings.DANDI_DOI_PUBLISH
    # Use the DANDI test datacite instance as a placeholder if PREFIX isn't set
    prefix = settings.DANDI_DOI_API_PREFIX or '10.80507'
    dandiset_id = version.dandiset.identifier
    version_id = version.version
    metadata = version.metadata
    if version_doi:
        doi = f'{prefix}/dandi.{dandiset_id}/{version_id}'
    else:
        doi = f'{prefix}/dandi.{dandiset_id}'
        # Dandiset DOI is the same as version url without version
        metadata['url'] = metadata['url'].rsplit('/', 1)[0]
    metadata['doi'] = doi
    # TODO(asmacdo) findable dois
    # datacite_body = to_datacite(metadata, event=event)
    datacite_payload = to_datacite(metadata)
    return (doi, datacite_payload)

def create_or_update_doi(datacite_payload: dict) -> str:
    if not doi_configured():
        print("DOI NOT CONFIGURED!!!")
        return

    doi = datacite_payload["data"]["attributes"]["doi"]
    url = settings.DANDI_DOI_API_URL
    auth = requests.auth.HTTPBasicAuth(settings.DANDI_DOI_API_USER, settings.DANDI_DOI_API_PASSWORD)

    try:
        response = requests.post(url, json=datacite_payload, auth=auth, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 422:
            # Retry with PUT if DOI already exists
            update_url = f"{url}/{doi}"
            try:
                update_response = requests.put(update_url, json=datacite_payload, auth=auth, timeout=30)
                update_response.raise_for_status()
            except Exception:
                logger.exception('Failed to update existing DOI %s', doi)
                logger.exception(datacite_payload)
                if e.response:
                    logger.exception(e.response.text)
                raise
        else:
            logger.exception('Failed to create DOI %s', doi)
            logger.exception(datacite_payload)
            if e.response:
                logger.exception(e.response.text)
            raise


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
