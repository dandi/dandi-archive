# Garbage collection
There are several kinds of data that exist without being included in a dandiset, meaning they are simply taking up space in the system.
These data should be cleaned up automatically after some time.

# Data types
## Uploads
As part of the multipart upload process, an `Upload` database record is created to track the status of the upload.
`Upload`s can be orphaned when a client aborts the upload process before creating an `AssetBlob` from the `Upload`.

`Uploads` could be abandoned prior to any uploads, partially uploaded, or after upload is complete.
The preferred way to deal with partial uploads in S3 is to set up a [bucket lifecycle rule](https://aws.amazon.com/blogs/aws/s3-lifecycle-management-update-support-for-multipart-uploads-and-delete-markers/).
If the object is already uploaded, we can simply delete it from S3.
In all cases, we need to delete the database record.

`Upload`s should be deleted whenever the presigned URLs expire, which is currently set in `multipart.py#DandiMultipartMixin` to 7 days.

## AssetBlobs
After an upload is complete, it is converted into an `AssetBlob`, which is then registered with an `Asset`.
If a user skips this registration step, the file will be available in S3, but will not appear in any dandisets.

The referenced object in S3 needs to be deleted along with the database record.

Unreferenced `AssetBlob`s should be removed after 1 day to prevent malicious actors from storing files in our S3 bucket for any significant length of time.

## Assets
An `Asset` is simply an `AssetBlob` with a path and some metadata.
Because `Asset`s are immutable, "modifying" and `Asset` will actually create a new `Asset` object and replace the old `Asset`'s references with the new `Asset`. This results in a substantial number of orphaned `Asset` objects.

Deleting an `Asset` is as simple as deleting the database record, although it might also result in an orphaned `AssetBlob`.

Unreferenced `Asset`s should be removed after 30 days, just in case a user accidentally deletes some metadata that we need to recover.

## Embargoed AssetBlobs and Assets
Embargoed `AssetBlobs` and `Assets` should be subject to the same garbage collection rules as normal `AssetBlobs` and `Assets`.

## S3 objects
Hypothetically, we might at some point encounter a desynchronization between objects stored in S3 and references stored in the database.
We should identify up any objects stored in S3 that do not have corresponding `AssetBlob`s.
We should also identify and `AssetBlob`s that do not have corresponding objects in S3.

Deleting the blobs is an easy API call.
Identifying problematic objects requires iterating over every blob in the archive, which would take a while.

Orphaned data should not be cleaned up automatically, as they are likely a symptom of a bug.
Instead, they should be investigated manually as they occur.
There should be a scheduled job that runs and reports orphaned data somewhere, either throwing an exception to be reported in Sentry, or be saving some data somewhere to be displayed in the admin data dashboard.

## ZarrArchives
A `ZarrArchive` represents a single zarr file being stored at a specific prefix in S3.

`ZarrArchives` may be large enough that deleting automatically may result in fairly catastrophic data loss, so no automatic garbage collection should be done.
Instead, `ZarrArchives` that have not been modified in more than 30 days should be logged for manual review.

# Implementation
All of these garbage collection operations should be added to the `collect_garbage` script.

The actual implementation of these operations should be added to `dandiapi.api.garbage`.

After thoroughly testing the script by hand in staging/production, a Celery Beat task should be created that checks for stale data nightly.

All of these numbers should be available in the admin data dashboard so that we can independently verify that the scheduled task is working correctly.
