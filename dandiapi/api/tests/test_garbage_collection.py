from __future__ import annotations

from django.utils import timezone
from freezegun import freeze_time
import pytest

from dandiapi.api.models import (
    AssetBlob,
    GarbageCollectionEvent,
    GarbageCollectionEventRecord,
    Upload,
)
from dandiapi.api.services import garbage_collection


@pytest.mark.django_db
def test_garbage_collect_uploads(upload_factory):
    # Create an expired upload by setting its created date to the past.
    # We have to do this in an UPDATE query, because using the `created` kwarg in the factory
    # doesn't work. `freezegun.freeze_time` doesn't work either, because MinIO complains
    # about the system clock being skewed.
    expired_upload: Upload = upload_factory()
    expired_upload.created = timezone.now() - garbage_collection.UPLOAD_EXPIRATION_TIME
    expired_upload.save()

    non_expired_upload: Upload = upload_factory()

    assert garbage_collection._garbage_collect_uploads() == 1

    assert Upload.objects.filter(id=non_expired_upload.id).exists()
    assert not Upload.objects.filter(id=expired_upload.id).exists()


@pytest.mark.django_db
def test_garbage_collect_asset_blobs(asset_factory, asset_blob_factory):
    # Case 1: AssetBlob is orphaned, and older than the expiration time
    orphaned_expired_asset_blob: AssetBlob = asset_blob_factory()
    orphaned_expired_asset_blob.created = (
        timezone.now() - garbage_collection.ASSET_BLOB_EXPIRATION_TIME
    )
    orphaned_expired_asset_blob.save()

    # Case 2: AssetBlob is orphaned, but is newer than the expiration time
    orphaned_non_expired_asset_blob: AssetBlob = asset_blob_factory()

    # Case 3: AssetBlob is not orphaned, but is older than the expiration time
    non_orphaned_expired_asset_blob: AssetBlob = asset_blob_factory()
    non_orphaned_expired_asset_blob.created = (
        timezone.now() - garbage_collection.ASSET_BLOB_EXPIRATION_TIME
    )
    non_orphaned_expired_asset_blob.save()
    asset_factory(blob=non_orphaned_expired_asset_blob)

    # Case 4: AssetBlob is not orphaned, and is newer than the expiration time
    non_orphaned_non_expired_asset_blob: AssetBlob = asset_blob_factory()
    asset_factory(blob=non_orphaned_non_expired_asset_blob)

    # Only Case 1 should be garbage collected
    assert garbage_collection._garbage_collect_asset_blobs() == 1
    assert not AssetBlob.objects.filter(id=orphaned_expired_asset_blob.id).exists()
    assert AssetBlob.objects.filter(id=orphaned_non_expired_asset_blob.id).exists()
    assert AssetBlob.objects.filter(id=non_orphaned_expired_asset_blob.id).exists()
    assert AssetBlob.objects.filter(id=non_orphaned_non_expired_asset_blob.id).exists()


@pytest.mark.django_db
def test_garbage_collection_event_records(asset_blob_factory, upload_factory, mocker):
    # Mock GARBAGE_COLLECTION_EVENT_CHUNK_SIZE to reduce the time of this test
    mocker.patch.object(garbage_collection, 'GARBAGE_COLLECTION_EVENT_CHUNK_SIZE', 1)

    # Create enough asset blobs to create 3 GarbageCollectionEvents
    asset_blob_count = garbage_collection.GARBAGE_COLLECTION_EVENT_CHUNK_SIZE * 2 + 1
    garbage_collected_asset_blobs: list[AssetBlob] = []
    for _ in range(asset_blob_count):
        asset_blob: AssetBlob = asset_blob_factory()
        asset_blob.created = timezone.now() - garbage_collection.ASSET_BLOB_EXPIRATION_TIME
        asset_blob.save()
        garbage_collected_asset_blobs.append(asset_blob)

    # Create enough uploads to create 3 GarbageCollectionEvents
    upload_count = garbage_collection.GARBAGE_COLLECTION_EVENT_CHUNK_SIZE * 2 + 1
    garbage_collected_uploads: list[Upload] = []
    for _ in range(upload_count):
        upload: Upload = upload_factory()
        upload.created = timezone.now() - garbage_collection.UPLOAD_EXPIRATION_TIME
        upload.save()
        garbage_collected_uploads.append(upload)

    garbage_collection.garbage_collect()

    # Make sure the garbage collected DB records are deleted
    assert all(
        not AssetBlob.objects.filter(id=asset_blob.id).exists()
        for asset_blob in garbage_collected_asset_blobs
    )
    assert all(
        not Upload.objects.filter(id=upload.id).exists() for upload in garbage_collected_uploads
    )

    # Make sure the garbage collected asset blob and upload objects are deleted from S3
    assert all(
        not asset_blob.blob.storage.exists(asset_blob.blob.name)
        for asset_blob in garbage_collected_asset_blobs
    )
    assert all(
        not upload.blob.storage.exists(upload.blob.name) for upload in garbage_collected_uploads
    )

    # Make sure the GarbageCollectionEvent records are created
    assert GarbageCollectionEvent.objects.count() == 2
    assert GarbageCollectionEvent.objects.filter(type=AssetBlob.__name__).count() == 1
    assert GarbageCollectionEvent.objects.filter(type=Upload.__name__).count() == 1

    assert GarbageCollectionEventRecord.objects.count() == asset_blob_count + upload_count
    assert (
        GarbageCollectionEventRecord.objects.filter(event__type=AssetBlob.__name__).count()
        == asset_blob_count
    )
    assert (
        GarbageCollectionEventRecord.objects.filter(event__type=Upload.__name__).count()
        == upload_count
    )

    # Make sure running garbage_collect() again doesn't delete the GarbageCollectionEvent
    # records yet
    with freeze_time(time_to_freeze=timezone.now()):
        garbage_collection.garbage_collect()
        assert GarbageCollectionEvent.objects.count() == 2
        assert GarbageCollectionEventRecord.objects.count() == asset_blob_count + upload_count

    # Make sure the GarbageCollectionEvent records are deleted after the RESTORATION_WINDOW
    with freeze_time(time_to_freeze=timezone.now() + garbage_collection.RESTORATION_WINDOW):
        garbage_collection.garbage_collect()
        assert GarbageCollectionEvent.objects.count() == 0
        assert GarbageCollectionEventRecord.objects.count() == 0
