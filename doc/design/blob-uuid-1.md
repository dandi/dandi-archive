A blob is referenced by a key generation function. the value of this key is used to index the blob in the database table of identities and on the s3 storage. `s3://dandiarchive/blob/<3digitskey>/<next3digitskey>/<restofkey>`

** database table of identities **: indexed by the key and contains columns for as many types of checksums as we want. these checksums constitute identities of the blob and should use functions that will always return the same value.

**key generation function**: the current suggestion (from satra) for this function is UUID4.

**DANDI ETag generation function**: this is an agreement between API server and DANDI CLI for now to ensure there is an algorithm that consistently returns the correct number of parts given a `contentSize` in bytes. this should in theory also be the AWS ETag generation function.

## Upload (from a CLI)

### Check process (for de-duplication):
1. CLI sends expected digest with digest type (e.g., ETag)
2. API checks for existence of ETag in identity table.
3. if exists, returns key, if not returns an error.

### Blob upload process:
1. CLI initiates upload sending contentSize + ETag
2. API generates key, determines upload location `s3://dandiarchive/blob/<3digitskey>/<next3digitskey>/<key>`
4. API saves initial data (size, ETAG, key) to Upload table
3. API returns presigned URLs
4. CLI verifies that the number+size of parts match the calculated number of parts (i.e. server and CLI are using the same ETag generation function)
5. CLI uploads to presigned URLs, and for each part checks ETag on return. Any part upload failure can be retried without involving API.
6. CLI sends part info to API, API responds with presigned completion URL
7. CLI completes upload and checks final ETag. Mismatch aborts the upload.
8. API validates the size and that the initially reported ETag matches the actual ETag
9. Check for collision, since some other task could have finished by this time with the same object
10. API adds key + ETag to Asset table, delete from Upload table
11. API kicks off background process to calculate checksums

## Garbage Collection process

1. if dangling key's are found, API does garbage collection on keys that are older than 24 hours.
2. sends background process info about deleted keys

## Out of band background process

1. Receives key from API and queues up a job to process the blob
2. performs a set of tasks on blob including multi checksum computation.
3. adds checksums to object metadata
4. pings api that checksums are ready
5. API adds checksums to row in blob db

References:

- original issue/discussion: https://github.com/dandi/dandi-api/issues/146#issuecomment-793114637
