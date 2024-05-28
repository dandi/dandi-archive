from __future__ import annotations
import hashlib

from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
import djclick as click

from dandiapi.api.models import AssetBlob
from dandiapi.api.services.asset import add_asset_to_version
from dandiapi.api.services.dandiset import create_dandiset
from dandiapi.api.services.metadata import validate_asset_metadata, validate_version_metadata
from dandiapi.api.tasks import calculate_sha256


@click.command()
@click.option('--name', default='Development Dandiset')
@click.option('--owner', 'email', required=True, help='The email address of the owner')
@click.option('--first_name', default='Randi The Admin')
@click.option('--last_name', default='Dandi')
def create_dev_dandiset(name: str, email: str, first_name: str, last_name: str):
    owner = User.objects.get(email=email)
    owner.first_name = first_name
    owner.last_name = last_name
    owner.save()

    version_metadata = {
        'description': 'An informative description',
        'license': ['spdx:CC0-1.0'],
    }
    for i in range(1, 21):
        name = f"version_{i}"
        _, draft_version = create_dandiset(user=owner, embargo=False, version_name=name,
                                        version_metadata=version_metadata)

        file_size = 20
        file_content = b'A' * file_size
        uploaded_file = SimpleUploadedFile(name='foo/bar.txt', content=file_content)
        etag = '76d36e98f312e98ff908c8c82c8dd623-0'

        try:
            asset_blob = AssetBlob.objects.get(etag=etag)
        except AssetBlob.DoesNotExist:
            # Since the SimpleUploadedFile is non-zarr asset, validation fails
            # without a sha2_256 initially provided.
            sha256_hash = hashlib.sha256(file_content).hexdigest()
            asset_blob = AssetBlob(
                blob_id=uuid4(), blob=uploaded_file, etag=etag, size=file_size, sha256=sha256_hash
            )
            asset_blob.save()
        asset_metadata = {
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
            'encodingFormat': 'text/plain',
            'schemaKey': 'Asset',
            'path': 'foo/bar.txt',
        }
        asset = add_asset_to_version(
            user=owner, version=draft_version, asset_blob=asset_blob, metadata=asset_metadata
        )

        calculate_sha256(blob_id=asset_blob.blob_id)
        validate_asset_metadata(asset=asset)
        validate_version_metadata(version=draft_version)
