import logging
import os

from dandischema.datacite import to_datacite
from django.conf import settings
import requests

from dandiapi.api.models import Version


def _generate_doi_data(version: Version):
    if settings.DANDI_ALLOW_LOCALHOST_URLS:
        # If this environment variable is set, the pydantic model will allow URLs with localhost
        # in them. This is important for development and testing environments, where URLs will
        # frequently point to localhost.
        os.environ['DANDI_ALLOW_LOCALHOST_URLS'] = 'True'
    from dandischema.datacite import to_datacite

    prefix = settings.DANDI_DOI_API_PREFIX or '10.00000'
    dandiset_id = version.dandiset.identifier
    version_id = version.version
    doi = f'{prefix}/{dandiset_id}/{version_id}'
    metadata = version.metadata.metadata
    metadata['doi'] = doi
    return (doi, to_datacite(metadata))


def create_doi(version: Version) -> str:
    doi, request_body = _generate_doi_data(version)
    # If DOI isn't configured, skip the API call
    if (
        settings.DANDI_DOI_API_URL is not None
        or settings.DANDI_DOI_API_USER is not None
        or settings.DANDI_DOI_API_PASSWORD is not None
        or settings.DANDI_DOI_API_PREFIX is not None
    ):
        try:
            requests.post(
                settings.DANDI_DOI_API_URL,
                json=request_body,
                auth=requests.auth.HTTPBasicAuth(
                    settings.DANDI_DOI_API_USER,
                    settings.DANDI_DOI_API_PASSWORD,
                ),
            ).raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.error('Failed to create DOI %s', doi)
            logging.error(request_body)
            raise e
    return doi
