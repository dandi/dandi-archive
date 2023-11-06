# Upload and Asset Blob Garbage Collection

## Background

Now that the [design for S3 trailing delete](./s3-trailing-delete.md) is deployed to staging, we are ready to implement garbage collection. [This older design document](./garbage-collection-1.md#uploads) is still relevant, and summarizes the various types of garbage collection we want to implement. This document will present a design for garbage collection of uploads and asset blobs, i.e. garbage that accumulates due to improper uploads done by users. A design for garbage collection of orphaned “Assets” (i.e. files that have been properly uploaded, have metadata, etc. but are no longer associated with any version of a dandiset) is more complex and is left for a future design document. Additionally, the garbage collection process in this design document only applies to regular assets; garbage collection of Zarrs is not covered.

## Why do we need garbage collection?

When a user creates an asset, they send a request to the API and the API returns a series of presigned URLs for the user to perform a multipart upload to. Then, an `Upload` database row is created to track the status of the upload. When the user is done uploading their data to the presigned URLs, they must “finalize” the upload by sending a request to the API to create an `AssetBlob` out of that `Upload`. Finally, they must make one more request to actually associate this new `AssetBlob` with an `Asset`.

### Orphaned Asset Uploads

If the user cancels a multipart upload partway through, or completes the multipart upload to S3 but does not “finalize” the upload, then the upload becomes “orphaned”, i.e. the associated `Upload` record and S3 object remain in the database/bucket indefinitely.

### Orphaned AssetBlobs

In this case, assume that the user properly completes the multipart upload flow and “finalizes” the `Upload` record such that it is now an `AssetBlob`, but they do not send a request to associate the new blob with an `Asset`. That `AssetBlob` record and associated S3 object will remain in the database/bucket indefinitely.

## Implementation

We will introduce a new celery-beat task that runs daily. This task will

- Query for and delete any uploads that are older than the multipart upload presigned URL expiration time (this is currently 7 days).
- Query for and delete any AssetBlobs that are (1) not associated with any Assets, and (2) older than 7 days.

In both cases, we need to delete both the blob from S3 and the row from the DB in order to avoid getting into an inconsistent state.

Due to the trailing delete lifecycle rule, the actual uploaded data will remain recoverable for up to 30 days after this deletion, after which the lifecycle rule will clear it out of the bucket permanently.

## Data

The current amount of orphaned data in the system as of 11/6/2023 is as follows:

Orphaned `Uploads`: 740

Orphaned `AssetBlobs`: 5

Orphaned `Assets`: 175,545
