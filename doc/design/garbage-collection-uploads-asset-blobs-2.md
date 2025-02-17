# Upload and Asset Blob Garbage Collection

This document presents a design for garbage collection of uploads and asset blobs in the context of the S3 trailing delete feature. It explains the need for garbage collection and describes the scenarios of orphaned uploads and orphaned asset blobs. The implementation involves introducing a new daily task to query and delete uploads and asset blobs that meet certain criteria. The document also mentions the recoverability of uploaded data and provides a link to a GitHub PR providing the implementation.

## Background

Now that the [design for S3 trailing delete](https://github.com/dandi/dandi-archive/blob/master/doc/design/s3-trailing-delete.md) is deployed, we are ready to implement next stages in garbage collection. [This older design document](https://github.com/dandi/dandi-archive/blob/master/doc/design/garbage-collection-1.md#uploads) is still relevant, and summarizes the various types of garbage collection we want to implement. This document will present a design for garbage collection of `Upload`s and `AssetBlob`s, i.e. garbage that accumulates due to improper uploads done by users. A design for garbage collection of orphaned `Asset`s (i.e. files that have been properly uploaded, have metadata, etc. but are not associated with any Dandisets) is more complex and is left for a future design document.

## Why do we need garbage collection?

When a user creates an asset, they send a request to the API and the API returns a series of presigned URLs for the user to perform a multipart upload to. Then, an `Upload` database row is created to track the status of the upload. When the user is done uploading their data to the presigned URLs, they must "finalize" the upload by sending a request to the API to create an `AssetBlob` out of that `Upload`. Finally, they must make one more request to actually associate this new `AssetBlob` with an `Asset`.

### Orphaned Uploads

If the user cancels a multipart upload partway through, or completes the multipart upload to S3 but does not "finalize" the upload, then the upload becomes "orphaned", i.e. the associated `Upload` record and S3 object remain in the database/bucket indefinitely.

### Orphaned AssetBlobs

For this case there are two scenarios - (1)  the user properly completes the multipart upload flow and "finalizes" the `Upload` record such that it is now an `AssetBlob`, but they do not send a request to associate the new blob with an `Asset`, or (2) an `Asset` is garbage collected (yet to be implemented), leaving its corresponding `AssetBlob` "orphaned". In both cases, the `AssetBlob` record and associated S3 object will remain in the database/bucket indefinitely.

## Implementation Details

We will introduce a new celery-beat task that runs daily. This task will

- Query for and delete any uploads that are older than the multipart upload presigned URL expiration time (this is currently 7 days).
- Query for and delete any AssetBlobs that are (1) not associated with any Assets, and (2) older than 7 days.

Due to the trailing delete lifecycle rule, the actual uploaded data will remain recoverable for up to 30 days after this deletion, after which the lifecycle rule will clear it out of the bucket permanently.

In order to facilitate restoration of deleted data, as well as for general auditability of the garbage collection feature, two new database tables will be created to store information on garbage-collection events. Rows in this new table will be garbage-collected themselves every 30 days, since that is the number of days that the trailing delete feature waits before deleting expired object versions. In other words, once the blob is no longer recoverable via trailing delete in S3, the corresponding `GarbageCollectionEvent` and its associated `GarbageCollectionEventRecords` should be deleted as well.

### Garbage collection event table

```python
from django.db import models

class GarbageCollectionEvent(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=255)

class GarbageCollectionEventRecord(models.Model):
    event = models.ForeignKey(GarbageCollectionEvent)
    record = models.JSONField()
```

Note: the `record` field is a JSON serialization of the garbage-collected QuerySet, generated using [Django’s JSON model serializer](https://docs.djangoproject.com/en/5.1/topics/serialization/#serialization-formats-json)). This gives us the minimum information needed to restore a blob. The idea is that this can be reused for garbage collection of `Assets` as well.

## Implementation
See [PR #2087](https://github.com/dandi/dandi-archive/pull/2087) for the implementation.
