A blob is referenced by a key generation function. the value of this key is used to index the blob in the database table of identities and on the s3 storage. `s3://dandiarchive/blob/<3digitskey>/<next3digitskey>/<key>`

** database table of identities **: indexed by the key and contains columns for as many types of checksums as we want. these checksums constitute identities of the blob and should use functions that will always return the same value.

**key generation function**: the current suggestion (from satra) for this function is UUID4.

**DANDI ETag generation function**: this is an agreement between API server and DANDI CLI for now to ensure there is an algorithm that consistently returns the correct number of parts given a `contentSize` in bytes. this should in theory also be the AWS ETag generation function.

## Upload (from a CLI)

### Check process (for de-duplication):
1. CLI `POST /blobs/digests/` <-- `{"algorithm": "dandi:dandi-etag", "value": "123etag123"}`. API:
    1. Looks for an existing AssetBlob with the given digest(s).
    2. If it exists, return the `blobs:blob_id`.
    3. It it doesn't exist, return 404.
2. If 404, start upload process.
3. if `blob_id`, call `POST .../assets/` with the `blob_id` to register the new asset.

### Blob upload process:
1. CLI `/uploads/initialize` <-- `{"content_size": 12345 , "digest": {"algorithm": "dandi:dandi-etag", "value": "..."}`. API:
   1. Checks if there is already an asset blob with the given digest. If so, return 409 CONFLICT with the `blobs:blob_id` in the header (`Location`?).
   2. generates key, determines upload location `s3://dandiarchive/blob/<3digitskey>/<next3digitskey>/<key>`
   3. saves initial data (size, ETag, key) to Upload table
   4. API returns `uploads:upload_id` and presigned URLs
4. CLI verifies that the number+size of parts match the calculated number of parts (i.e. server and CLI are using the same ETag generation function)
5. CLI uploads to presigned URLs, and for each part checks ETag on return. Any part upload failure can be retried without involving API.
6. `/uploads/{upload_id}/complete/`: CLI sends parts info to API, API responds with presigned completion URL
7. CLI completes upload and checks final ETag. Mismatch aborts the upload.
8. CLI `POST /uploads/{upload_id}/validate/` <-- `{}` --> `blobs:key`. API
    1. validates the size and that the initially reported ETag matches the actual ETag
    2. checks for collision, since some other task could have finished by this time with the same object
        1. no collision - adds key + ETag to AssetBlob table, delete from Upload table.
        2. there is collision - deletes `blobs:blob_id` record, `uploads:upload_id` record, and `s3://dandiarchive/blob/<3digitskey>/<next3digitskey>/<key>`, will return key of an existing record
    4. kicks off background process to calculate checksums
9. CLI calls `POST .../assets/` with the `blob_id` to register the new asset.

## Garbage Collection process

1. if dangling keys (not used by any asset) are found, API does garbage collection on keys that are older than 24 hours.
2. sends background process info about deleted keys

## Out of band background process

1. Receives key from API and queues up a job to process the blob
2. performs a set of tasks on blob including multi checksum computation.
3. adds checksums to the AssetBlob row in the DB (initially they are null or something)
4. API injects checksums into metadata whenever it is requested: initially it won't be there while being calculated, but will magically appear after calculations finish.

References:

- original issue/discussion: https://github.com/dandi/dandi-api/issues/146#issuecomment-793114637
