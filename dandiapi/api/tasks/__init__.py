from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

from dandiapi.api.doi import delete_doi
from dandiapi.api.manifests import (
    write_assets_jsonld,
    write_assets_yaml,
    write_collection_jsonld,
    write_dandiset_jsonld,
    write_dandiset_yaml,
)
from dandiapi.api.models import Asset, AssetBlob, Dandiset, Version

logger = get_task_logger(__name__)


@shared_task(queue='calculate_sha256', soft_time_limit=86_400)
def calculate_sha256(blob_id: str) -> None:
    asset_blob = AssetBlob.objects.get(blob_id=blob_id)
    logger.info('Found AssetBlob %s', blob_id)
    sha256 = asset_blob.blob.storage.sha256_checksum(asset_blob.blob.name)

    # TODO: Run dandi-cli validation

    asset_blob.sha256 = sha256
    asset_blob.save()


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

    asset: Asset = Asset.objects.filter(id=asset_id, status=Asset.Status.PENDING).first()
    if asset:
        validate_asset_metadata(asset=asset)


@shared_task(soft_time_limit=30)
def validate_version_metadata_task(version_id: int) -> None:
    from dandiapi.api.services.metadata import validate_version_metadata

    version: Version = Version.objects.get(id=version_id)
    validate_version_metadata(version=version)


@shared_task
def delete_doi_task(doi: str) -> None:
    delete_doi(doi)


@shared_task
def publish_dandiset_task(dandiset_id: int):
    from dandiapi.api.services.publish import _publish_dandiset

    _publish_dandiset(dandiset_id=dandiset_id)
