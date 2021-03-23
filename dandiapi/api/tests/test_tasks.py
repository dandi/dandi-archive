import hashlib

from django.core.files.storage import Storage
import pytest

from dandiapi.api import tasks
from dandiapi.api.models import AssetBlob


@pytest.mark.django_db
def test_calculate_checksum_task(storage: Storage, asset_blob_factory):
    # Pretend like AssetBlob was defined with the given storage
    AssetBlob.blob.field.storage = storage

    asset_blob = asset_blob_factory(sha256=None)

    h = hashlib.sha256()
    h.update(asset_blob.blob.read())
    sha256 = h.hexdigest()

    tasks.calculate_sha256(asset_blob.blob_id)

    asset_blob.refresh_from_db()

    assert asset_blob.sha256 == sha256
