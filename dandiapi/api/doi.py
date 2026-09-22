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


def format_doi(dandiset_id: str, version: str) -> str:
    instance_name: str = get_instance_config().instance_name
    return f'{settings.DANDI_DOI_API_PREFIX}/{instance_name.lower()}.{dandiset_id}/{version}'


def _doi_url(doi: str) -> str:
    return settings.DANDI_DOI_API_URL.rstrip('/') + '/' + doi


def _auth() -> requests.auth.HTTPBasicAuth:
    return requests.auth.HTTPBasicAuth(settings.DANDI_DOI_API_USER, settings.DANDI_DOI_API_PASSWORD)


def _log_http_error(message: str, e: requests.exceptions.HTTPError) -> None:
    logger.exception(message)
    if e.response is not None:
        logger.exception(e.response.text)


def get_doi_state(doi: str) -> str | None:
    """Return the DataCite state of a DOI (draft, registered or findable), or None if absent."""
    if not doi_configured():
        return None
    try:
        r = requests.get(
            _doi_url(doi), headers={'Accept': 'application/vnd.api+json'}, auth=_auth(), timeout=30
        )
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == requests.codes.not_found:
            return None
        _log_http_error(f'Failed to fetch data for DOI {doi}', e)
        raise
    return r.json()['data']['attributes']['state']


def reserve_doi(doi: str) -> None:
    """Create a Draft DOI carrying only its identifier, so that the string is claimed."""
    if not doi_configured():
        logger.debug('Skipping DOI reservation for %s since not configured', doi)
        return
    r = requests.post(
        settings.DANDI_DOI_API_URL,
        json={'data': {'type': 'dois', 'attributes': {'doi': doi}}},
        auth=_auth(),
        timeout=30,
    )
    # DataCite reports an already-existing DOI as a 422. A Draft left over from an earlier
    # aborted publish is safe to reuse; any other state means the identifier is already real.
    if r.status_code == requests.codes.unprocessable_entity and get_doi_state(doi) == 'draft':
        logger.info('Reusing existing draft DOI %s', doi)
        return
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        _log_http_error(f'Failed to reserve DOI {doi}', e)
        raise


def promote_doi(version: Version) -> None:
    """
    Send a version's full metadata to its reserved DOI.

    When DANDI_DOI_PUBLISH is set this promotes the DOI to Findable, which is idempotent on an
    already-Findable DOI; otherwise the DOI stays a Draft with its metadata filled in.
    """
    from dandischema.datacite import to_datacite

    if not doi_configured():
        logger.debug('Skipping DOI promotion for %s since not configured', version.doi)
        return
    request_body = to_datacite(version.metadata, publish=settings.DANDI_DOI_PUBLISH)
    try:
        requests.put(
            _doi_url(version.doi), json=request_body, auth=_auth(), timeout=30
        ).raise_for_status()
    except requests.exceptions.HTTPError as e:
        _log_http_error(f'Failed to promote DOI {version.doi}', e)
        logger.exception(request_body)
        raise


def hide_doi(doi: str, *, url: str) -> None:
    """Demote a Findable DOI to Registered, pointing it at `url` as its tombstone."""
    if not doi_configured():
        logger.debug('Skipping DOI hiding for %s since not configured', doi)
        return
    request_body = {'data': {'type': 'dois', 'attributes': {'event': 'hide', 'url': url}}}
    try:
        requests.put(_doi_url(doi), json=request_body, auth=_auth(), timeout=30).raise_for_status()
    except requests.exceptions.HTTPError as e:
        _log_http_error(f'Failed to hide DOI {doi}', e)
        raise


def delete_doi(doi: str) -> None:
    """Delete a DOI if it is still a Draft, which is the only state DataCite allows deleting."""
    if not doi_configured():
        logger.debug('Skipping DOI deletion for %s since not configured', doi)
        return
    state = get_doi_state(doi)
    if state is None:
        logger.warning('Tried to delete nonexistent DOI %s', doi)
        return
    if state != 'draft':
        logger.warning('Not deleting DOI %s since it is %s, not draft', doi, state)
        return
    try:
        requests.delete(_doi_url(doi), auth=_auth(), timeout=30).raise_for_status()
    except requests.exceptions.HTTPError as e:
        _log_http_error(f'Failed to delete DOI {doi}', e)
        raise
