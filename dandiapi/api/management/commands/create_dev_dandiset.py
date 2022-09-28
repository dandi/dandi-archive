from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
import djclick as click

from dandiapi.api.models import Asset, AssetBlob
from dandiapi.api.services.dandiset import create_dandiset
from dandiapi.api.tasks import calculate_sha256, validate_asset_metadata, validate_version_metadata


@click.command()
@click.option('--name', default='Development Dandiset')
@click.option('--owner', required=True, help='The email address of the owner')
def create_dev_dandiset(name: str, owner: str):
    owner = User.objects.get(email=owner)

    version_metadata = {
        'description': 'An informative description',
        'license': ['spdx:CC0-1.0'],
    }
    _, draft_version = create_dandiset(
        user=owner, embargo=False, version_name=name, version_metadata=version_metadata
    )

    uploaded_file = SimpleUploadedFile(name='foo/bar.txt', content=b'A' * 20)
    etag = '76d36e98f312e98ff908c8c82c8dd623-0'
    try:
        asset_blob = AssetBlob.objects.get(etag=etag)
    except AssetBlob.DoesNotExist:
        asset_blob = AssetBlob(
            blob_id=uuid4(),
            blob=uploaded_file,
            etag=etag,
            size=20,
        )
        asset_blob.save()
    asset_metadata = {
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        'encodingFormat': 'text/plain',
        'schemaKey': 'Asset',
    }
    asset = Asset(blob=asset_blob, metadata=asset_metadata, path='foo/bar.txt')
    asset.save()
    draft_version.assets.add(asset)

    calculate_sha256(blob_id=asset_blob.blob_id)
    validate_asset_metadata(asset_id=asset.id)
    validate_version_metadata(version_id=draft_version.id)
