from datetime import datetime
from typing import Dict

from django.conf import settings
import requests

from dandiapi.api.models import Version


def _generate_doi_data(version: Version):
    prefix = settings.DANDI_DOI_API_PREFIX
    dandiset_id = version.dandiset.identifier
    version_id = version.version
    doi = f'{prefix}/{dandiset_id}/{version_id}'
    url = f'https://dandiarchive.org/dandiset/{dandiset_id}/{version_id}'
    creators = []
    contributors = []
    if 'contributor' in version.metadata.metadata:
        creators = [
            {'name': contributor['name']}
            for contributor in version.metadata.metadata['contributor']
            if 'dandi:Author' in contributor['roleName']
        ]
        contributors = [
            {'name': contributor['name']}
            for contributor in version.metadata.metadata['contributor']
        ]
    return (
        doi,
        {
            'data': {
                'id': doi,
                'type': 'dois',
                'attributes': {
                    'doi': doi,
                    'creators': creators,
                    'titles': [{'title': version.name}],
                    'publisher': 'DANDI Archive',
                    'publicationYear': datetime.now().year,
                    'contributors': contributors,
                    'types': {'resourceTypeGeneral': 'NWB'},
                    'url': url,
                },
            }
        },
    )


def create_doi(version: Version) -> str:
    # If DOI isn't configured, skip this step
    if (
        settings.DANDI_DOI_API_URL is None
        and settings.DANDI_DOI_API_USER is None
        and settings.DANDI_DOI_API_PASSWORD is None
        and settings.DANDI_DOI_API_PREFIX is None
    ):
        return
    doi, request_body = _generate_doi_data(version)
    requests.post(
        settings.DANDI_DOI_API_URL,
        json=request_body,
        auth=requests.auth.HTTPBasicAuth(
            settings.DANDI_DOI_API_USER,
            settings.DANDI_DOI_API_PASSWORD,
        ),
    ).raise_for_status()
    return doi
