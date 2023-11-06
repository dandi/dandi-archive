from contextlib import contextmanager
import os
import tempfile
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.core.files.base import File
from rest_framework.renderers import JSONRenderer
import yaml

from dandiapi.api.models import Asset, AssetBlob, Version
from dandiapi.api.storage import create_s3_storage


def s3_url(path: str):
    """Turn an object path into a fully qualified S3 URL."""
    storage = create_s3_storage(settings.DANDI_DANDISETS_BUCKET_NAME)
    signed_url = storage.url(path)
    # Strip off the query parameters from the presigning, as they are different every time
    parsed = urlparse(signed_url)
    return urlunparse((parsed[0], parsed[1], parsed[2], '', '', ''))


def _manifests_path(version: Version):
    return (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}'
    )


def manifest_location(version: Version):
    """Calculate the manifestLocation field for a Version."""
    if version.version == 'draft':
        return [
            (
                f'{settings.DANDI_API_URL}/api/dandisets/{version.dandiset.identifier}'
                f'/versions/draft/assets/'
            )
        ]
    return [s3_url(assets_yaml_path(version))]


def dandiset_jsonld_path(version: Version):
    return f'{_manifests_path(version)}/dandiset.jsonld'


def assets_jsonld_path(version: Version):
    return f'{_manifests_path(version)}/assets.jsonld'


def dandiset_yaml_path(version: Version):
    return f'{_manifests_path(version)}/dandiset.yaml'


def assets_yaml_path(version: Version):
    return f'{_manifests_path(version)}/assets.yaml'


def collection_jsonld_path(version: Version):
    return f'{_manifests_path(version)}/collection.jsonld'


@contextmanager
def streaming_file_upload(path: str, mode: str = 'w'):
    temp_file_name = None

    try:
        with tempfile.NamedTemporaryFile(mode=mode, delete=False) as outfile:
            temp_file_name = outfile.name
            yield outfile

        # Piggyback on the AssetBlob storage since we want to store manifests in the same bucket
        storage = AssetBlob.blob.field.storage
        with open(temp_file_name, 'rb') as temp_file:
            storage._save(path, File(temp_file))
    finally:
        if temp_file_name:
            os.remove(temp_file_name)


def write_dandiset_jsonld(version: Version):
    with streaming_file_upload(dandiset_jsonld_path(version)) as stream:
        stream.write(JSONRenderer().render(version.metadata).decode())


def write_assets_jsonld(version: Version):
    # Use full metadata when writing externally
    assets_metadata = (
        asset.full_metadata for asset in version.assets.select_related('blob', 'zarr').iterator()
    )
    with streaming_file_upload(assets_jsonld_path(version)) as stream:
        stream.write('[')
        for i, obj in enumerate(assets_metadata):
            if i > 0:
                stream.write(',')
            stream.write(JSONRenderer().render(obj).decode())

        stream.write(']')


def write_dandiset_yaml(version: Version):
    with streaming_file_upload(dandiset_yaml_path(version)) as stream:
        yaml.dump(version.metadata, stream, Dumper=yaml.CSafeDumper, allow_unicode=True)


def _yaml_dump_sequence_from_generator(stream, generator):
    for obj in generator:
        for i, line in enumerate(
            yaml.dump(obj, Dumper=yaml.CSafeDumper, allow_unicode=True).splitlines()
        ):
            if i == 0:
                prefix = '- '
            else:
                prefix = '  '

            stream.write(f'{prefix}{line}\n')


def write_assets_yaml(version: Version):
    with streaming_file_upload(assets_yaml_path(version)) as stream:
        _yaml_dump_sequence_from_generator(
            stream,
            # Use full metadata when writing externally
            (
                asset.full_metadata
                for asset in version.assets.select_related('blob', 'zarr')
                .order_by('created')
                .iterator()
            ),
        )


def write_collection_jsonld(version: Version):
    asset_ids = [
        Asset.dandi_asset_id(asset_id)
        for asset_id in version.assets.values_list('asset_id', flat=True)
    ]
    with streaming_file_upload(collection_jsonld_path(version)) as stream:
        stream.write(
            JSONRenderer()
            .render(
                {
                    '@context': version.metadata['@context'],
                    'id': version.metadata['id'],
                    '@type': 'prov:Collection',
                    'hasMember': asset_ids,
                },
            )
            .decode()
        )
