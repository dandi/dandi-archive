from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.transaction import atomic
from rest_framework_yaml.renderers import YAMLRenderer

from dandiapi.api.checksum import calculate_sha256_checksum
from dandiapi.api.models import AssetBlob, Version

logger = get_task_logger(__name__)


@shared_task
@atomic
def calculate_sha256(blob_id: int) -> None:
    logger.info('Starting sha256 calculation for blob %s', blob_id)
    asset_blob = AssetBlob.objects.get(blob_id=blob_id)

    sha256 = calculate_sha256_checksum(asset_blob.blob.storage, asset_blob.blob.name)
    logger.info('Calculated sha256 %s', sha256)

    # TODO: Run dandi-cli validation

    logger.info('Saving sha256 %s to blob %s', sha256, blob_id)

    asset_blob.sha256 = sha256
    asset_blob.save()


@shared_task
@atomic
def write_yamls(version_id: int) -> None:
    logger.info('Writing dandiset.yaml and assets.yaml for version %s', version_id)
    version: Version = Version.objects.get(id=version_id)

    # Piggyback on the AssetBlob storage since we want to store .yamls in the same bucket
    storage = AssetBlob.blob.field.storage

    dandiset_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/dandiset.yaml'
    )
    if storage.exists(dandiset_yaml_path):
        logger.info('%s already exists, deleting it', dandiset_yaml_path)
        storage.delete(dandiset_yaml_path)
    logger.info('Saving %s', dandiset_yaml_path)
    dandiset_yaml = YAMLRenderer().render(version.metadata.metadata)
    storage.save(dandiset_yaml_path, ContentFile(dandiset_yaml))

    assets_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/assets.yaml'
    )
    if storage.exists(assets_yaml_path):
        logger.info('%s already exists, deleting it', assets_yaml_path)
        storage.delete(assets_yaml_path)
    logger.info('Saving %s', assets_yaml_path)
    assets_yaml = YAMLRenderer().render(
        [asset.generate_metadata(version) for asset in version.assets.all()]
    )
    storage.save(assets_yaml_path, ContentFile(assets_yaml))

    logger.info('Wrote dandiset.yaml and assets.yaml for version %s', version_id)
