import logging

from django.conf import settings
import requests

from dandiapi.api.models import Version

# All of the required DOI configuration settings
DANDI_DOI_SETTINGS = [
    (settings.DANDI_DOI_API_URL, 'DANDI_DOI_API_URL'),
    (settings.DANDI_DOI_API_URL, 'DANDI_DOI_API_USER'),
    (settings.DANDI_DOI_API_PASSWORD, 'DANDI_DOI_API_PASSWORD'),
    (settings.DANDI_DOI_API_PREFIX, 'DANDI_DOI_API_PREFIX'),
]


def doi_configured() -> bool:
    return any(setting is not None for setting, _ in DANDI_DOI_SETTINGS)


def _generate_doi_data(version: Version):
    from dandischema.datacite import to_datacite

    publish = settings.DANDI_DOI_PUBLISH
    # Use the DANDI test datacite instance as a placeholder if PREFIX isn't set
    prefix = settings.DANDI_DOI_API_PREFIX or '10.80507'
    dandiset_id = version.dandiset.identifier
    version_id = version.version
    doi = f'{prefix}/dandi.{dandiset_id}/{version_id}'
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
            logging.exception('Failed to create DOI %s', doi)
            logging.exception(request_body)
            if e.response:
                logging.exception(e.response.text)
            raise
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
                if e.response and e.response.status_code == 404:
                    logging.warning('Tried to get data for nonexistent DOI %s', doi)
                    return
                else:
                    logging.exception('Failed to fetch data for DOI %s', doi)
                    raise
            if r.json()['data']['attributes']['state'] == 'draft':
                try:
                    s.delete(doi_url).raise_for_status()
                except requests.exceptions.HTTPError:
                    logging.exception('Failed to delete DOI %s', doi)
                    raise
