# Zarr Support
A zarr archive contains directories and zarr files. 
Zarr archives are stored in their entirety in S3.
Zarr archives are represented by a single Asset through the API.
A tree hash is computed as the zarr archive is uploaded.
The tree hash details (all nodes) are stored on S3 to avoid bloating the DB.
The intended use of Zarr archives is primarily to support use cases where data are too big to be copied or to be stored in a single file due to available storage limits. However, Zarr archives can be small as well.

# Requirements
1. Zarr archives are stored in a "directory" in S3.
1. Each zarr archive corresponds to a single Asset.
1. The CLI uses some kind of tree hashing scheme to compute a checksum for the entire zarr archive.
1. The API verifies the checksum immediately after upload, so the validation status is available in the response to the upload REST request.
1. The system can theoretically handle zarr files with ~1 million subfiles, each of size 64 * 64 * 64 bytes ~= 262 kilobytes.
1. Zarr metadata must be mutable for zarr files in draft dandisets.
1. Zarr archives must not be copied, as they are too large to reasonably store multiple copies.
1. Zarr archives are immutable as long as they are contained by a published dandiset.

# Implementation

## API endpoints
* **POST /api/zarr/**

  Create a new zarr archive and mint a UUID for it which would become `zarr_id`

  Returns the `zarr_id`

* **GET /api/zarr/{zarr_id}/**

  Returns some information about the zarr archive, like name, S3 path+url, and checksum

* **GET /api/zarr/{zarr_id}/{path}**

  When the path exists in S3, returns some information about the zarr file, like name, S3 path+url, and checksum.
  When the path is a directory in S3, returns a paginated list of files and directories. 
  Returns 404 if the path is not present in S3.

* **GET /api/zarr/{zarr_id}/upload/**

  Returns a 204 if an upload is in progress, or a 404 if an upload is not in progress.

* **POST /api/zarr/{zarr_id}/upload/**

  Ask to upload a batch of zarr files as part of the zarr archive.
  No more batch uploads are permitted until this one is completed or aborted.

  Requires a list of file paths and ETags (md5 checksums).
  The number of files being uploaded must be less than some experimentally defined limit (say ~500).
  If the limit is exceeded, return response 400.
  This limit should be chosen so that no upload requests can conceivably exceed the Heroku request timeout (30s).
  The file paths may include already uploaded files; this is how updates are done.

  Returns a list of presigned upload URLs

* **POST /api/zarr/{zarr_id}/upload/complete/**

  Completes an upload of a batch of zarr files.
  Fail if any of the checksums do not match.
  Trigger the task which recursively updates the tree hash for every parent node for each child.

* **DELETE /api/zarr/{zarr_id}/upload/**

  Cancels a batch upload.
  Any files already uploaded are deleted.
  A new batch upload can then be started.

* **DELETE /api/zarr/{zarr_id}/files/**

  Deletes zarr files from S3, and trigger the task to recursively update the tree hash accordingly.
  Requires a list of file paths.
  All paths must be present in S3, otherwise return 404 without deleting anything.

* **POST /api/dandisets/{...}/versions/{...}/assets/**

  Augments the existing endpoint to create a new Asset that points to the zarr archive.
  Requires a `zarr_id` in the request body instead of a `blob_id`.
  Return an asset ID

When added to a dandiset, zarr archives will appear as a normal `Asset` in all the asset API endpoints.
The asset metadata will contain the information required to determine if an asset is a normal file blob or a zarr file.

## Storage implementation
A zarr archive with a `zarr_id` `c1223302-aff4-44aa-bd4b-952aed997c78` is stored in the public S3 bucket: `dandiarchive/zarr/c1223302-aff4-44aa-bd4b-952aed997c78/...`

Paths for zarr files, or any assets in the archive, should never use a `/` prefix.
`foo/bar.txt` is correct, `/foo/bar.txt` is not.

If a client uploaded a file `1/2/3/foo.bar`, it would be stored at `dandiarchive/zarr/c1223302-aff4-44aa-bd4b-952aed997c78/1/2/3/foo.bar`.

To avoid polluting the zarr archive data, tree hash checksums are stored next to the zarr archive: `dandiarchive/zarr_checksums/c1223302-aff4-44aa-bd4b-952aed997c78/...`
The algorithm used to generate the checksum files themselves is described below.

## Upload flow
1. The client `POST`s to create a new zarr archive, or uses existing API endpoints to find the `zarr_id` of a zarr asset to modify.
1. The client identifies some files in the zarr archive that it wants to upload.
1. The client calculates the MD5 of each file. 
1. The client sends the paths+MD5s to `POST .../upload/` and receives a list of presigned upload URLs.
   * The size of the batch sent can be tuned by the client, up to a certain maximum.
   * Larger batches mean less overhead, but more data to retry in case of failure.
1. The client uses the presigned upload URLs to upload the files to S3.
1. The client notifies the API it is finished with `POST .../upload/complete/`.
   * The API verifies that all the files are present in S3 and have the correct ETag.
   * If everything is fine, the upload is marked complete and a new upload can begin.
1. The client repeats from step 2 until everything is uploaded.

If the zarr archive is ever stuck with a pending upload, that upload can be cancelled by any client.

If any zarr files needs to be deleted from the archive, they can be deleted in bulk using `DELETE .../files/` (up to a certain maximum).

## Tree hashing scheme
To avoid having to store a checksum in the database for every directory in every zarr file, we will delegate the storage of the checksums to S3.

### Storing tree hash nodes
For every subdirectory in the zarr archive, a `.checksum` file is also stored in S3 to track the tree hash (algorithm described below).

If a zarr archive `c1223302-aff4-44aa-bd4b-952aed997c78` contained only a single file `1/2/3/foo.bar`, the following `.checksum` files would be generated:

* dandiarchive/zarr_checksums/c1223302-aff4-44aa-bd4b-952aed997c78/1/2/3/.checksum
* dandiarchive/zarr_checksums/c1223302-aff4-44aa-bd4b-952aed997c78/1/2/.checksum
* dandiarchive/zarr_checksums/c1223302-aff4-44aa-bd4b-952aed997c78/1/.checksum
* dandiarchive/zarr_checksums/c1223302-aff4-44aa-bd4b-952aed997c78/.checksum

The last `.checksum` contains the final tree hash for the entire zarr archive.

### .checksum file format
Each zarr file and directory in the archive has a path and a checksum (`md5`).
For files, this is simply the ETag.
For directories, it is calculated like so:
1. List all immediate child files and directories in JSON objects like `{"md5":"12345...67890","path":"foo/bar"}` (key order matters).
1. Create an object `{"directories":[...],"files":[...]}` (key order matters) containing those child objects, ordered alphabetically by `path`.
1. Take the resulting JSON list, serialize it to a string, and take the MD5 hash of that string.

For every directory in the zarr archive, the API server maintains a `.checksum` file which contains the checksum of the directory, and also the checksums of the directory contents for easier updates.
The `.checksum` file is stored in JSON format, exactly like the format used to calculate the checksum:
```
{"checksums":{"directories":[{"md5":"abc...def","path":"foo/baz"},...],"files":[{"md5":"12345...67890","path":"foo/bar"},...]},"md5":"09876...54321"}
```

To update a `.checksum` file, the API server simply needs to read the existing contents, modify `checksums` to reflect the new state of the zarr archive, serialize and calculate the MD5, then save the new contents.

Every update to a `.checksum` file also requires updating the `.checksum` of the parent directory, since the `md5` of the child has change.
This bubbles up to the top of the zarr archive, where the final `.checksum` for the entire archive can be found.

No spaces are used in JSON encodings.

## Calculating checksums
Experience has proven that updating the .checksum file in the upload complete request takes too long.
Therefore, updating the `.checksum` file happens in a celery task.
The upload complete endpoint will enqueue updates to perform, which are then handled as soon as possible by an arbitrary number of celery workers.
This allows us to scale the number of celery workers so that the checksum for a zarr archive is available almost immediately after upload is complete.

### ZarrChecksumUpdate
The `ZarrChecksumUpdate` model is used to store updates that need to be applied to a zarr archive.
It's fields will include:
* The `ZarrArchive` it applies to.
* The `parent_directory` containing the `.checksum` file being modified.
* The `name` of the file being changed in the `parent_directory`.
* An `update_type` enum:
  * `FILE`: adding or updating a file checksum
  * `DIRECTORY`: adding or updating a directory checksum
  * `REMOVAL`: removing a checksum
* The `depth` of the update; basically the number of slashes in `parent_directory`.
* A `status` enum:
  * `PENDING`: not yet picked up by a worker
  * `IN_PROGRESS`: being processed by a worker


In the upload complete endpoint, a new `ZarrChecksumUpdate` is created with an `update_type` of `FILE` for every path.
In the file delete endpoint, a new `ZarrChecksumUpdate` is created with an `update_type` of `REMOVAL` for every path.
Both endpoints will then dispatch a single checksum update task.

### Checksum update task
The checksum update task takes a `zarr_id` as an argument.
It will then run the following loop:
* Select the `ZarrChecksumUpdate` with the greatest `depth` and status `PENDING`.
  * If there is no such `ZarrChecksumUpdate`, terminate.
* Select for update all `ZarrChecksumUpdate` with the same `parent_directory`.
  These represent all the updates waiting to be applied to a `.checksum` file.
  * If the select for update failed, another worker selected the same `parent_directory` in a race condition.
    Catch the error and terminate silently.
* Set the `status` of all selected `ZarrChecksumUpdates` to `IN_PROGRESS`.
* Dispatch another checksum update task.
  If there are other updates pending, it will begin saturating the available workers.
  If there are no updates pending, it will quit silently without doing anything.
* Apply the necessary modifications to the `.checksum` file in the common `parent_directory`.
* Delete all selected `ZarrChecksumUpdates`.
* Repeat until there are no more pending `ZarrChecksumUpdates`.

This task is guaranteed to:
* Update from the bottom of the file tree to the top, minimizing writes.
* Never apply the same updates at the same time when run concurrently.
* Saturate the worker pool as quickly as possible.

# Publishing support
After a dandiset that contains a zarr archive is published, that zarr archive is immutable.
This ensures that published dandisets are truly immutable.

Immutability is enforced by disabled the upload and delete endpoints for the zarr archive.

The client needs to agressively inform users that publishing a dandiset with a zarr archive will render that zarr archive immutable.