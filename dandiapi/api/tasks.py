from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.transaction import atomic
import jsonschema.exceptions
import requests
from rest_framework_yaml.renderers import YAMLRenderer

from dandiapi.api.checksum import calculate_sha256_checksum
from dandiapi.api.models import Asset, AssetBlob, AssetStatus, Version

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

    # Trigger metadata validation on all assets pointing to this blob
    for asset in asset_blob.assets.all():
        for version in asset.versions:
            validate_asset_metadata.delay(version.id, asset.id)


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


# TODO what is a reasonable retry delay
@shared_task(bind=True, default_retry_delay=10)
@atomic
# This method takes both a version_id and an asset_id because asset metadata renders differently
# depending on which version the asset belongs to.
def validate_asset_metadata(self, version_id: int, asset_id: int) -> None:
    logger.info('Validating asset metadata for asset %s, version %s', asset_id, version_id)
    asset = Asset.objects.get(id=asset_id)
    version = Version.objects.get(id=version_id)

    if asset.status == AssetStatus.VALIDATING.name:
        # Another task is currently validating, let it finish
        logger.info('Asset %s is already being validated, wait for it to complete', asset_id)
        raise self.retry()

    # Begin the validation process so no other validation tasks will run simultaneously
    asset.status = AssetStatus.VALIDATING.name
    asset.save()

    try:
        metadata = asset.generate_metadata(version)
        if 'schemaVersion' not in metadata:
            logger.info('schemaVersion not specified in metadata for asset %s', asset_id)
            asset.status = AssetStatus.INVALID.name
            asset.validation_error = 'schemaVersion not specified'
            asset.save()
            return
        schema_version = metadata['schemaVersion']
        schema_url = (
            'https://raw.githubusercontent.com/dandi/schema/master/'
            f'releases/{schema_version}/asset.json'
        )
        request = requests.get(schema_url)
        request.raise_for_status()
        schema = request.json()
        jsonschema.validate(instance=metadata, schema=schema)
    except jsonschema.exceptions.ValidationError as ve:
        logger.info('Validation error for asset %s', asset_id)

        asset.status = AssetStatus.INVALID.name
        asset.validation_error = format_validation_error(ve)
        asset.save()
        return
    except Exception as e:
        logger.error('Error while validating asset %s', asset_id)
        logger.error(str(e))
        asset.status = AssetStatus.INVALID.name
        asset.validation_error = str(e)
        asset.save()
        return
    logger.info('Successfully validated asset %s', asset_id)
    asset.status = AssetStatus.VALID.name
    asset.validation_error = ''
    asset.save()
