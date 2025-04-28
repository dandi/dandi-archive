from __future__ import annotations

from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
import djclick as click

from dandiapi.api.models import AssetBlob
from dandiapi.api.services.asset import add_asset_to_version
from dandiapi.api.services.dandiset import create_dandiset
from dandiapi.api.services.metadata import validate_asset_metadata, validate_version_metadata
from dandiapi.api.services.permissions.dandiset import add_dandiset_owner
from dandiapi.api.tasks import calculate_sha256


@click.command()
@click.option('--name', default='Development Dandiset')
@click.option('--owner', 'email', required=True, help='The email address of the owner')
@click.option(
    '--num-extra-owners',
    'num_extra_owners',
    required=False,
    type=int,
    default=0,
    show_default=True,
    help='The number of extra owners to programmatically generate',
)
def create_dev_dandiset(*, name: str, email: str, num_extra_owners: int):
    owner = User.objects.get(email=email)

    version_metadata = {
        'description': 'An informative description',
        'license': ['spdx:CC0-1.0'],
    }
    dandiset, draft_version = create_dandiset(
        user=owner, embargo=False, version_name=name, version_metadata=version_metadata
    )

    if num_extra_owners:
        import faker

        fake = faker.Faker()
        for _ in range(num_extra_owners):
            user, _ = User.objects.get_or_create(
                username=fake.user_name(),
                defaults={
                    'email': fake.email(),
                    'password': fake.password(),
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                },
            )
            add_dandiset_owner(dandiset=dandiset, user=user)

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
        'path': 'foo/bar.txt',
    }
    asset = add_asset_to_version(
        user=owner, version=draft_version, asset_blob=asset_blob, metadata=asset_metadata
    )

    calculate_sha256(blob_id=asset_blob.blob_id)
    validate_asset_metadata(asset=asset)
    validate_version_metadata(version=draft_version)
