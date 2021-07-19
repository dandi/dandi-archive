from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.core.files.base import ContentFile
from rest_framework.renderers import JSONRenderer
from rest_framework_yaml.renderers import YAMLRenderer

from dandiapi.api.models import AssetBlob, Version
from dandiapi.api.storage import create_s3_storage


def _manifests_path(version: Version):
    return (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}'
    )


def dandiset_jsonld_path(version: Version):
    return f'{_manifests_path(version)}/dandiset.jsonld'


def assets_jsonld_path(version: Version):
    return f'{_manifests_path(version)}/assets.jsonld'


def dandiset_yaml_path(version: Version):
    return f'{_manifests_path(version)}/dandiset.yaml'


def assets_yaml_path(version: Version):
    return f'{_manifests_path(version)}/assets.yaml'


def s3_url(path: str):
    """Turn an object path into a fully qualified S3 URL."""
    storage = create_s3_storage(settings.DANDI_DANDISETS_BUCKET_NAME)
    signed_url = storage.url(path)
    parsed = urlparse(signed_url)
    s3_url = urlunparse((parsed[0], parsed[1], parsed[2], '', '', ''))
    return s3_url


def _write_manifest_file(path: str, metadata, logger):
    # Piggyback on the AssetBlob storage since we want to store manifests in the same bucket
    storage = AssetBlob.blob.field.storage

    if storage.exists(path):
        if logger:
            logger.info('%s already exists, deleting it', path)
        storage.delete(path)
    if logger:
        logger.info('Saving %s', path)
    storage.save(path, ContentFile(metadata))


def write_dandiset_jsonld(version: Version, logger=None):
    _write_manifest_file(
        dandiset_jsonld_path(version),
        JSONRenderer().render(version.metadata.metadata),
        logger,
    )


def write_assets_jsonld(version: Version, logger=None):
    _write_manifest_file(
        assets_jsonld_path(version),
        JSONRenderer().render([asset.metadata.metadata for asset in version.assets.all()]),
        logger,
    )


def write_dandiset_yaml(version: Version, logger=None):
    _write_manifest_file(
        dandiset_yaml_path(version),
        YAMLRenderer().render(version.metadata.metadata),
        logger,
    )


def write_assets_yaml(version: Version, logger=None):
    _write_manifest_file(
        assets_yaml_path(version),
        YAMLRenderer().render([asset.metadata.metadata for asset in version.assets.all()]),
        logger,
    )
