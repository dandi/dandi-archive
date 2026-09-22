from __future__ import annotations

from typing import TYPE_CHECKING

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from django.contrib.auth.models import User
import requests

from dandiapi.api.doi import delete_doi, get_doi_state, hide_doi, promote_doi
from dandiapi.api.mail import send_dandiset_unembargo_failed_message
from dandiapi.api.manifests import (
    write_assets_jsonld,
    write_assets_yaml,
    write_collection_jsonld,
    write_dandiset_jsonld,
    write_dandiset_yaml,
)
from dandiapi.api.models import Asset, AssetBlob, Version
from dandiapi.api.models.dandiset import Dandiset

if TYPE_CHECKING:
    from uuid import UUID

logger = get_task_logger(__name__)


@shared_task(soft_time_limit=60)
def remove_asset_blob_embargoed_tag_task(blob_id: str) -> None:
    from dandiapi.api.services.embargo import remove_asset_blob_embargoed_tag

    asset_blob = AssetBlob.objects.get(blob_id=blob_id)
    remove_asset_blob_embargoed_tag(asset_blob)


@shared_task(
    queue='calculate_sha256',
    soft_time_limit=86_400,  # 24 hours
    autoretry_for=(SoftTimeLimitExceeded,),
    retry_backoff=True,
    max_retries=3,
)
def calculate_sha256(blob_id: str | UUID) -> None:
    asset_blob = AssetBlob.objects.get(blob_id=blob_id)
    logger.info('Calculating sha256 checksum for asset blob %s', blob_id)
    sha256 = asset_blob.blob.storage.sha256_checksum(asset_blob.blob.name)

    # TODO: Run dandi-cli validation

    AssetBlob.objects.filter(blob_id=blob_id).update(sha256=sha256)


@shared_task(soft_time_limit=180)
def write_manifest_files(version_id: int) -> None:
    version: Version = Version.objects.get(id=version_id)
    logger.info('Writing manifests for version %s:%s', version.dandiset.identifier, version.version)

    write_dandiset_yaml(version)
    write_assets_yaml(version)
    write_dandiset_jsonld(version)
    write_assets_jsonld(version)
    write_collection_jsonld(version)


@shared_task(soft_time_limit=10)
def validate_asset_metadata_task(asset_id: int) -> None:
    from dandiapi.api.services.metadata import validate_asset_metadata

    asset: Asset | None = Asset.objects.filter(id=asset_id, status=Asset.Status.PENDING).first()
    if asset:
        validate_asset_metadata(asset=asset)
    else:
        logger.debug('Asset %s not found or already validated', asset_id)


@shared_task(soft_time_limit=30)
def validate_version_metadata_task(version_id: int) -> None:
    from dandiapi.api.services.metadata import validate_version_metadata

    version: Version = Version.objects.get(id=version_id)
    validate_version_metadata(version=version)


def _is_terminal_datacite_error(e: requests.RequestException) -> bool:
    """Whether a DataCite failure is one that retrying will not fix, e.g. rejected metadata."""
    response = e.response
    return (
        response is not None
        and requests.codes.bad_request <= response.status_code < requests.codes.server_error
        and response.status_code != requests.codes.too_many_requests
    )


def _retry_after(e: requests.RequestException, retries: int) -> int:
    response = e.response
    retry_after = response.headers.get('Retry-After', '') if response is not None else ''
    if retry_after.isdigit():
        return int(retry_after)
    return min(60 * 2**retries, 3600)


@shared_task(bind=True, max_retries=8, soft_time_limit=120)
def promote_version_doi_task(self, version_id: int) -> None:
    """Send a published version's metadata to its reserved DOI, promoting it to Findable."""
    version: Version = Version.objects.get(id=version_id)
    try:
        promote_doi(version)
    except requests.RequestException as e:
        if not _is_terminal_datacite_error(e) and self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=_retry_after(e, self.request.retries)) from e
        logger.exception(
            'Giving up on promoting DOI %s for version %s:%s',
            version.doi,
            version.dandiset.identifier,
            version.version,
        )
        raise


@shared_task
def retire_version_doi_task(doi: str, landing_url: str) -> None:
    """Hide or delete the DOI of a deleted version, depending on its DataCite state."""
    if get_doi_state(doi) == 'findable':
        hide_doi(doi, url=landing_url)
    else:
        delete_doi(doi)


@shared_task
def publish_dandiset_task(dandiset_id: int, user_id: int):
    from dandiapi.api.services.publish import _publish_dandiset

    _publish_dandiset(dandiset_id=dandiset_id, user_id=user_id)


@shared_task(soft_time_limit=1200)
def unembargo_dandiset_task(dandiset_id: int, user_id: int):
    from dandiapi.api.services.embargo import unembargo_dandiset

    ds = Dandiset.objects.get(pk=dandiset_id)
    user = User.objects.get(id=user_id)

    # If the unembargo fails for any reason, send an email, but continue the error propagation
    try:
        unembargo_dandiset(ds, user)
    except Exception:
        send_dandiset_unembargo_failed_message(ds)
        raise
