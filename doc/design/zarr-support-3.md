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
  Also, recursively update the tree hash for every parent node for each child.

* **DELETE /api/zarr/{zarr_id}/upload/**

  Cancels a batch upload.
  Any files already uploaded are deleted.
  A new batch upload can then be started.

* **DELETE /api/zarr/{zarr_id}/files/**

  Deletes zarr files from S3, and updates the tree hash accordingly.
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

To avoid polluting the zarr archive data, only the root checksum is stored in the database. All subdirectory tree hash checksums (including the root) are stored next to the zarr archive: `dandiarchive/zarr_checksums/c1223302-aff4-44aa-bd4b-952aed997c78/...`
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

### Zarr entry checksum format
Each zarr file and directory in the archive has a path and a checksum.
For files, this is simply the MD5 ETag.
For directories, it is calculated like so:
1. List all immediate child files and directories in JSON objects like `{"digest":"12345...67890","name":"foo","size":69105}` (key order matters).
    - The size of a directory is the sum of the sizes of all files recursively within it.
1. Create an object `{"directories":[...],"files":[...]}` (key order matters) containing those child objects, ordered alphabetically by `name`.
1. Take the resulting JSON object, serialize it to a string (escaping all non-ASCII characters and with no spaces between tokens), and take the MD5 hash of that string.
1. The final checksum for the directory is then a string of the form `{md5_digest}-{file_count}--{size}`, where `file_count` is the total number of files recursively within the directory and `size` is the sum of their sizes.

### .checksum file format
For every directory in the zarr archive, the API server maintains a `.checksum` file which contains the checksum of the directory, and also the checksums of the directory contents for easier updates.
The `.checksum` file is stored in JSON format, exactly like the format used to calculate the checksum:
```
{"checksums":{"directories":[{"digest":"abc...def-10--23","name":"foo","size":69105},...],"files":[{"digest":"12345...67890","name":"bar","size":42},...]},"digest":"09876...54321-501--65537"}
```

To update a `.checksum` file, the API server simply needs to read the existing contents, modify `checksums` to reflect the new state of the zarr archive, serialize and calculate the MD5, then save the new contents.

Every update to a `.checksum` file also requires updating the `.checksum` of the parent directory, since the `digest` of the child has changed.
This bubbles up to the top of the zarr archive, where the final `.checksum` for the entire archive can be found.

No spaces are used in JSON encodings.

# Publishing support
After a dandiset that contains a zarr archive is published, that zarr archive is immutable.
This ensures that published dandisets are truly immutable.

Immutability is enforced by disabled the upload and delete endpoints for the zarr archive.

The client needs to aggressively inform users that publishing a dandiset with a zarr archive will render that zarr archive immutable.
