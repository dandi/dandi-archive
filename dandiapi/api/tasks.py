import os

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.transaction import atomic
import jsonschema.exceptions
from rest_framework_yaml.renderers import YAMLRenderer

from dandiapi.api.checksum import calculate_sha256_checksum
from dandiapi.api.models import Asset, AssetBlob, Version

if settings.DANDI_ALLOW_LOCALHOST_URLS:
    # If this environment variable is set, the pydantic model will allow URLs with localhost
    # in them. This is important for development and testing environments, where URLs will
    # frequently point to localhost.
    os.environ['DANDI_ALLOW_LOCALHOST_URLS'] = 'True'

from dandischema.metadata import validate

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

    # The newly calculated sha256 digest will be included in the metadata, so we need to revalidate
    for asset in asset_blob.assets.all():
        validate_asset_metadata.delay(asset.id)


@shared_task
@atomic
def write_yamls(version_id: int) -> None:
    logger.info('Writing dandiset.yaml and assets.yaml for version %s', version_id)
    version: Version = Version.objects.get(id=version_id)

    # Piggyback on the AssetBlob storage since we want to store .yamls in the same bucket
    storage = AssetBlob.blob.field.storage

    dandiset_yaml_path = version.dandiset_yaml_path
    if storage.exists(dandiset_yaml_path):
        logger.info('%s already exists, deleting it', dandiset_yaml_path)
        storage.delete(dandiset_yaml_path)
    logger.info('Saving %s', dandiset_yaml_path)
    dandiset_yaml = YAMLRenderer().render(version.metadata.metadata)
    storage.save(dandiset_yaml_path, ContentFile(dandiset_yaml))

    assets_yaml_path = version.assets_yaml_path
    if storage.exists(assets_yaml_path):
        logger.info('%s already exists, deleting it', assets_yaml_path)
        storage.delete(assets_yaml_path)
    logger.info('Saving %s', assets_yaml_path)
    assets_yaml = YAMLRenderer().render([asset.metadata.metadata for asset in version.assets.all()])
    storage.save(assets_yaml_path, ContentFile(assets_yaml))

    logger.info('Wrote dandiset.yaml and assets.yaml for version %s', version_id)


def format_as_index(indices):
    """Render a JSON schema path as a series of indices."""
    if not indices:
        return ''
    return '[%s]' % ']['.join(repr(index) for index in indices)


def format_validation_error(error: jsonschema.exceptions.ValidationError):
    """
    Succinctly format a ValidationError.

    The default __str__ for ValidationError includes the entire schema, so we simplify it.
    """
    return f'{error.message}\nSee: metadata{format_as_index(error.relative_path)}'  # noqa: B306


class ValidationError(Exception):
    pass


@shared_task
@atomic
# This method takes both a version_id and an asset_id because asset metadata renders differently
# depending on which version the asset belongs to.
def validate_asset_metadata(asset_id: int) -> None:
    logger.info('Validating asset metadata for asset %s', asset_id)
    asset = Asset.objects.get(id=asset_id)

    asset.status = Asset.Status.VALIDATING
    asset.save()

    try:
        publish_asset = Asset.published_asset(asset)
        metadata = publish_asset.metadata.metadata
        validate(metadata, schema_key='PublishedAsset')
    except Exception as e:
        logger.error('Error while validating asset %s', asset_id)
        logger.error(str(e))
        asset.status = Asset.Status.INVALID
        asset.validation_error = str(e)
        asset.save()
        return
    logger.info('Successfully validated asset %s', asset_id)
    asset.status = Asset.Status.VALID
    asset.validation_error = ''
    asset.save()


@shared_task
@atomic
def validate_version_metadata(version_id: int) -> None:
    logger.info('Validating dandiset metadata for version %s', version_id)
    version: Version = Version.objects.get(id=version_id)

    version.status = Version.Status.VALIDATING
    version.save()

    try:
        publish_version = version.publish_version
        metadata = publish_version.metadata.metadata

        # Inject a dummy DOI so the metadata is valid
        metadata['doi'] = '10.80507/dandi.123456/0.123456.1234'

        validate(metadata, schema_key='PublishedDandiset')
    except Exception as e:
        logger.error('Error while validating version %s', version_id)
        logger.error(str(e))
        version.status = Version.Status.INVALID
        version.validation_error = str(e)
        version.save()
        return
    logger.info('Successfully validated version %s', version_id)
    version.status = Version.Status.VALID
    version.validation_error = ''
    version.save()
