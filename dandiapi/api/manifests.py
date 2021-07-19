from django.core.files.base import ContentFile
from rest_framework_yaml.renderers import YAMLRenderer

from dandiapi.api.models import AssetBlob, Version


def _write_manifest_file(path, metadata, logger):
    # Piggyback on the AssetBlob storage since we want to store manifests in the same bucket
    storage = AssetBlob.blob.field.storage

    if storage.exists(path):
        if logger:
            logger.info('%s already exists, deleting it', path)
        storage.delete(path)
    if logger:
        logger.info('Saving %s', path)
    storage.save(path, ContentFile(metadata))


def write_dandiset_yaml(version: Version, logger=None):
    _write_manifest_file(
        version.dandiset_yaml_path,
        YAMLRenderer().render(version.metadata.metadata),
        logger,
    )


def write_asset_yaml(version: Version, logger=None):
    _write_manifest_file(
        version.assets_yaml_path,
        YAMLRenderer().render([asset.metadata.metadata for asset in version.assets.all()]),
        logger,
    )
