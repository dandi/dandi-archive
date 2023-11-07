from __future__ import annotations

from contextlib import contextmanager
import tempfile
from typing import IO, TYPE_CHECKING, Any
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.core.files.base import File
from rest_framework.renderers import JSONRenderer
import yaml

from dandiapi.api.models import Asset, AssetBlob, Version
from dandiapi.api.storage import create_s3_storage

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable


def _s3_url(path: str) -> str:
    """Turn an object path into a fully qualified S3 URL."""
    storage = create_s3_storage(settings.DANDI_DANDISETS_BUCKET_NAME)
    signed_url = storage.url(path)
    # Strip off the query parameters from the presigning, as they are different every time
    parsed = urlparse(signed_url)
    return urlunparse((parsed[0], parsed[1], parsed[2], '', '', ''))


def _manifests_path(version: Version) -> str:
    return (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}'
    )


def manifest_location(version: Version) -> list[str]:
    """Calculate the manifestLocation field for a Version."""
    if version.version == 'draft':
        return [
            (
                f'{settings.DANDI_API_URL}/api/dandisets/{version.dandiset.identifier}'
                f'/versions/draft/assets/'
            )
        ]
    return [_s3_url(_assets_yaml_path(version))]


def _dandiset_jsonld_path(version: Version) -> str:
    return f'{_manifests_path(version)}/dandiset.jsonld'


def _assets_jsonld_path(version: Version) -> str:
    return f'{_manifests_path(version)}/assets.jsonld'


def _dandiset_yaml_path(version: Version) -> str:
    return f'{_manifests_path(version)}/dandiset.yaml'


def _assets_yaml_path(version: Version) -> str:
    return f'{_manifests_path(version)}/assets.yaml'


def _collection_jsonld_path(version: Version) -> str:
    return f'{_manifests_path(version)}/collection.jsonld'


@contextmanager
def _streaming_file_upload(path: str) -> Generator[IO[bytes], None, None]:
    with tempfile.NamedTemporaryFile(mode='r+b') as outfile:
        yield outfile
        outfile.seek(0)

        # Piggyback on the AssetBlob storage since we want to store manifests in the same bucket
        storage = AssetBlob.blob.field.storage
        storage._save(path, File(outfile))  # noqa: SLF001


def _yaml_dump_sequence_from_generator(stream: IO[bytes], generator: Iterable[Any]) -> None:
    for obj in generator:
        for i, line in enumerate(
            yaml.dump(
                obj, encoding='utf-8', Dumper=yaml.CSafeDumper, allow_unicode=True
            ).splitlines()
        ):
            stream.write(b'- ' if i == 0 else b'  ')
            stream.write(line)
            stream.write(b'\n')


def write_dandiset_jsonld(version: Version) -> None:
    with _streaming_file_upload(_dandiset_jsonld_path(version)) as stream:
        stream.write(JSONRenderer().render(version.metadata))


def write_assets_jsonld(version: Version) -> None:
    # Use full metadata when writing externally
    assets_metadata = (
        asset.full_metadata for asset in version.assets.select_related('blob', 'zarr').iterator()
    )
    with _streaming_file_upload(_assets_jsonld_path(version)) as stream:
        stream.write(b'[')
        for i, obj in enumerate(assets_metadata):
            if i > 0:
                stream.write(b',')
            stream.write(JSONRenderer().render(obj))

        stream.write(b']')


def write_dandiset_yaml(version: Version) -> None:
    with _streaming_file_upload(_dandiset_yaml_path(version)) as stream:
        yaml.dump(
            version.metadata, stream, encoding='utf-8', Dumper=yaml.CSafeDumper, allow_unicode=True
        )


def write_assets_yaml(version: Version) -> None:
    with _streaming_file_upload(_assets_yaml_path(version)) as stream:
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


def write_collection_jsonld(version: Version) -> None:
    asset_ids = [
        Asset.dandi_asset_id(asset_id)
        for asset_id in version.assets.values_list('asset_id', flat=True)
    ]
    with _streaming_file_upload(_collection_jsonld_path(version)) as stream:
        stream.write(
            JSONRenderer().render(
                {
                    '@context': version.metadata['@context'],
                    'id': version.metadata['id'],
                    '@type': 'prov:Collection',
                    'hasMember': asset_ids,
                },
            )
        )
