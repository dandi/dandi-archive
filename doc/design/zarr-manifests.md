# Zarr Versioning/Publishing support via Manifest Files

This document specifies

1. [x] *Zarr manifest files*, each of which describes a Zarr
in the Dandi Archive, including the Zarr's internal directory structure and
details on all of the Zarr's *entries* (regular, non-directory files).  The
Dandi Archive is to automatically generate these files and serve them via S3.
2. [ ] Changes needed to the DANDI Archive's API, DB Data Model, and internal logic.
3. [ ] Changes needed to AWS (S3 in particular; likely TerraForm) configuration.
4. [ ] Changes needed (if any) to dandischema.

## Current prototype

### Creating manifest files

Proof-of-concept implementation to produce manifest files for all Zarrs
in the Dandi Archive, and actual produced manifest files are provided from https://datasets.datalad.org/?dir=/dandi/zarr-manifests, which is a [DataLad dataset](https://handbook.datalad.org/en/latest/glossary.html#term-DataLad-dataset) with individual manifest files are annexed.

**Note:** https://datasets.datalad.org/dandi/zarr-manifests/zarr-manifests-v2-sorted/ and subfolders provides ad-hoc json record listing folders/files to avoid parsing stock apache2 index.

[CRON job](https://github.com/dandi/zarr-manifests/blob/master/cronjob) runs daily on typhon (server at Dartmouth) to create manifest files (only) for new/updated zarrs in the archive.
Except where noted, the manifest file format defined herein matches the format used by the proof of concept.
As embargoed access to Zarrs is not implemented yet, embargo-related designs here might be incomplete.

### Data access using manifest files

[dandidav](https://github.com/dandi/dandidav)---a WebDAV server for the DANDI---serves Zarrs from the Archive using the manifest files.
Actual data is served from the Archive's S3 bucket, but the WebDAV server uses the manifest files to determine the structure of the Zarrs and the versions of the Zarrs' entries.
Two "end-points" to access Zarrs within that namespace are provided, but only one of them uses Zarr manifests:

- [webdav.dandiarchive.org/zarrs](https://webdav.dandiarchive.org/zarrs) -- **uses manifests** for all Zarrs across all dandisets, possibly with multiple versions. E.g. see [zarrs/057/f84/057f84d5-a88b-490a-bedf-06f3f50e9e62](https://webdav.dandiarchive.org/zarrs/057/f84/057f84d5-a88b-490a-bedf-06f3f50e9e62) which ATM has 3 versions.
- [webdav.dandiarchive.org/dandisets/](https://webdav.dandiarchive.org/dandisets/)`{dandiset_id}/{version}/{path}/` -- **does not** use manifest files but gets listing directly from S3, so provides access only to the current version (possibly not even finalized yet during upload) of the zarr at that path.

Tools which support following redirections for individual files within Zarr can be pointed to the locations under the former end-point to "consume" zarr of a specific version.
ATM dandisets do not support publishing (versioning) of Zarrs, so there would be only `/draft/` versions of dandisets with Zarrs.
If this design is supported/implemented, particular versions of Zarrs would be made available from within particular versions of the `/dandisets/{dandiset_id}/`s.

## Proposed design

### Creating & Storing Manifest Files

Whenever DANDI Archive calculates the checksum for a Zarr in the Archive, it
shall additionally produce a *manifest file* listing various information about
the Zarr and its entries in the format described in the next section.  This
manifest file shall be stored in the Archive's S3 bucket at the path
`zarr-manifest/{dir1}/{dir2}/{zarr_id}/{checksum}.json`, where:

- `{dir1}` is replaced by the first three characters of the Zarr ID
- `{dir2}` is replaced by the next three characters of the Zarr ID
- `{zarr_id}` is replaced by the ID of the Zarr
- `{checksum}` is replaced by the Dandi Zarr checksum of the Zarr at that point
  in time

This directory structure (a) will allow `dandidav` to change the data source
for its `/zarr/` hierarchy from the proof-of-concept to the S3 bucket with
minimal code changes and (b) ensures that the number of entries within each
directory in the bucket under `zarr-manifest/` is not colossal, thereby
avoiding tremendous resource usage by `dandidav`.

**Embargo.** The manifest file shall be world-readable, unless the Zarr is embargoed or
belongs to an embargoed Dandiset, in which case appropriate steps shall be
taken to limit read access to the file. Related issues/aspects on zarrbargo:
- [? avoid dedicated EmbargoedZarrArchive](https://github.com/dandi/dandi-archive/issues/2003#issuecomment-2315718976)

Manifest files shall also be generated for all Zarrs already in the Archive
when this feature is first implemented.


### Manifest File Format

A Zarr manifest file is a JSON document consisting of a JSON object with the
following fields:

- `fields` (array of strings) — A list of the names of the fields provided for
  each entry in the `entries` tree.  The possible field names, along with
  descriptions of the entry fields, are as follows:

    - `"versionId"` — The S3 version ID (as a string) of the current version of
      the S3 object in which the entry is stored in the Archive's S3 bucket

        - **Implementation Note:** Obtaining an S3 object's current version ID
          requires using either (a) the `GetObject` S3 API call (for a single
          object) or (b) the `ListObjectVersions` S3 API call, including
          client-side filtering out of all non-latest entries (for all objects
          under a given common S3 prefix).

    - `"lastModified"` — The `LastModified` timestamp of the entry's S3 object
      as a string of the form `"YYYY-MM-DDTHH:MM:SS±HH:MM"`

    - `"size"` — The size in bytes of the entry as an integer

    - `"ETag"` — The `ETag` of the entry's S3 object as a string with leading &
      trailing double quotation marks (U+0022) removed (not counting the double
      quotation marks used by the JSON serialization)

        - This value is the same as the lowercase hexadecimal encoding of the
          entry's MD5 digest.

    It is **highly recommended** that `fields` always has a value of
    `["versionId", "lastModified", "size", "ETag"]`, in that order.

- `statistics` (object) — An object containing the following fields describing
  the Zarr as a whole:

    - `entries` — The total number of entries in the Zarr as an integer

    - `depth` — The maximum number of directory levels deep at which an entry
      can be found in the Zarr, as an integer

        - A Zarr containing only entries, no directories, has a depth of 0.

        - A Zarr that contains one or more top-level directories, all which
          contain only entries, has a depth of 1.

    - `totalSize` — The sum of the sizes of all entries in the Zarr

    - `lastModified` — The date & time at which any change was made to the
      Zarr's contents as a string of the form `"YYYY-MM-DDTHH:MM:SS±HH:MM"`

    - `zarrChecksum` — The Zarr's Dandi Zarr checksum

- `entries` (object) — A tree of values mirroring the directory & entry
  structure of the Zarr.

    - Each entry in the Zarr is represented as an array of the same length as
      the top-level `fields` field in which each element gives the Zarr entry's
      value for the field whose name is at the same location in `fields`.

        For example, if `fields` had a value of `["versionId", "lastModified",
        "size", "ETag"]`, then a possible entry array could be:

        ```json
        [
            "VI067uTlzPTTyL750Ibkx3hAUm67A_sI",
            "2022-03-16T02:39:36+00:00",
            27935,
            "fc3d1270cd950f1e5430226db4c38c0e"
        ]
        ```

        Here, the first element of the array is the entry's `versionId`, the
        second element is the entry's `lastModified` timestamp, the third
        element is the entry's size, and the fourth entry is the entry's ETag.

    - Each directory in the Zarr is represented as an object in which each key
      is the name of an entry or subdirectory inside the directory and the
      corresponding value is either an entry array or a directory object.

    - The `entries` object itself represents the top level directory of the
      Zarr.

    For example, a Zarr with the following structure:

    ```text
    .
    ├── .zgroup
    ├── arr_0/
    │   ├── .zarray
    │   └── 0
    └── arr_1/
        ├── .zarray
        └── 0
    ```

    would have an `entries` field as follows (with elements of the entry arrays
    omitted):

    ```json
    {
        ".zgroup": [ ... ],
        "arr_0": {
            ".zarray": [ ... ],
            "0": [ ... ]
        },
        "arr_1": {
            ".zarray": [ ... ],
            "0": [ ... ]
        }
    }
    ```

> [!NOTE]
> The manifest files created by @yarikoptic contain the following fields which
> are not present in the format described above:
>
> - A top-level `schemaVersion` key with a constant value of `2`
>
> - A `zarrChecksumMismatch` field inside the `statistics` object, used to
>   store the checksum that the API reports for a Zarr when it disagrees with
>   the checksum calculated by the manifest-generation code


### Archive Changes

#### Model/API Changes

***WIP***

* Zarr version IDs equal the Zarr checksum

- `Zarr` model has `.checksum`
  - (?) Not settable by client
  - (?) Upon changes to zarr asset initiated, `Zarr.checksum` reset to None, which stays such until Zarr is finalized
  - (?) Zarr should be denied new changes if `Zarr.checksum` is already None, and until it is finalized
  - Make `/finalize` to return new Zarr checksum:
    - might take awhile, so we might want to return some upload ID to be able to re-request checksum for specific upload
    - at this point we have not minted yet a new asset!
    - **Alternative**: do establish ZarrVersion
      - `many-to-many` between `zarr_id` and `zarr_version`.
      - `/finalize` would return new `zarr_version_id`
      - **Alternatives**:
        - PUT/PATCH/POST calls in API expecting `zarr_id` should be changed to provide `zarr_version_id` instead
        - We just add `/zarr/{zarr_id}/{zarr_version_id}/` call which would return `checksum` for that version.

* Side discussion: new Zarr version/checksum compute is relatively expensive.
  It could be "cheap" if we rely on prior manifest + changes (new files with checksums) or DELETEs. But it would require 'fsck' style re-check
  and possibly "fixing" the version. Fragile since there would be no state to describe some prior state of Zarr to "checksum" it.

* To not change DB model too much, to not breed zarr specific DB model fields, rely on `metadata.digest.dandi:dandi-zarr-checksum` for Zarr checksum.
  - Add `zarr_checksum` to `Zarr` model, but it must be just a convenience duplicate of the checksum in the metadata. But then some return of the API would need to be adjusted to return this dedicated `zarr_checksum` in addition to value in `metadata`
  - We mint new asset when metadata changes, so new asset is produced when metadata record with a new version of Zarr (new checksum) is provided
    - we verify that checksum is consistent with the the `checksum` of zarr_id provided
      - NOTE: this means we would not be able to re-use versioned zarr from released version!

* …/assets/ results gain `zarr_checksum`
  - they can only optionally contain `metadata` hence, we want to have `zarr_checksum` in the response
  - Q: What is "Version" int returned now for each asset?
  likely internal DB Version.id - unclear why it is in API response in such a form.
* …/assets/paths/ -- no change since point to `asset_id`

* …/assets/{asset_id}/download/ -- point to versioned version based on checksum in metadata
  * `webdav.{archive_domain}/zarrs/{dir1}/{dir2}/{zarr_id}/{checksum}/` URLs
        ([...redirect /download/ for zarrs to webdav](https://github.com/dandi/dandi-archive/issues/1993))
* Zarr `contentUrl`s:
    - Make API download URLs for Zarrs redirect to dandidav
    - Replace S3 URLs with `webdav.{archive_domain}/zarrs/{dir1}/{dir2}/{zarr_id}/{checksum}/` URLs
      ([...redirect /download/ for zarrs to webdav](https://github.com/dandi/dandi-archive/issues/1993)) ?
        - Document needed changes to dandidav?
            - The bucket for the Archive instance will now be given on the command line (only required if a custom/non-default API URL is given)
            - The bucket's region will have to be looked up & stored before starting the webserver
            - Zarrs under `/dandisets/` will no longer determine their S3 location via `contentUrl`; instead, they will combine the Archive's bucket & region with the Zarr ID in the asset properties (templated into "zarr/{zarr_id}/")

* Getting specific Zarr versions & their files from API endpoints
    - The current `/zarr/{zarr_id}/…` endpoints operate on the most recent version of the Zarr
    - `GET /zarr/{zarr_id}/versions/` (paginated)
    - `GET /zarr/{zarr_id}/versions/{version_id}/` ?
    - `GET /zarr/{zarr_id}/versions/{version_id}/files/[?prefix=...]` (paginated)
        - The Zarr entry objects returned in `…/files/` responses (with & without `versions/{version_id}/`) will need to gain a `VersionId` field containing the S3 object version ID
    - Nothing under /zarr/versions/ is writable over the API

* Publishing Dandisets with Zarrs: Just ensure that no entries/S3 object versions from the referenced version are ever deleted (see GC section below)

* Remove `.dandiset` attribute from [*ZarrArchive](https://github.com/dandi/dandi-archive/blob/HEAD/dandiapi/zarr/models.py#L101):
  - It should be possible to associate Zarr with multiple dandisets
  - GC should take care about picking up stale Zarrs as it does Blobs
  - Would remove `ingest_dandiset_zarrs` (seems to be just a service helper ATM anyways)

#### Garbage collection (GC)

* GC of Manifests: manifests older than X days (e.g. 30) can be deleted if not referenced by any Zarr asset (draft or published).
* GC of Manifests should trigger analysis/deletion of S3 objects based on their content:
  * if it is the last manifest(s) to be removed for a zarr, the zarr asset and `/zarr/{zarr_id}/` "folder" should be removed as well (including all versions of all keys);
  * upon deletion of a set of manifests for a `zarr_id`, collect key and versionId's referenced in those manifests but not in any other manifest for that Zarr, and delete those particular versions of those Keys from S3. If a key has no other versions, delete that key fully (do not keep lonely`DeleteMarker`)

### AWS Configuration Changes

`zarr/` prefix must be excluded from "trailing delete".
This necessary because a file within Zarr could be deleted in subsequent version, while still accessed by its VersionId in the previous one.
ATM there is no filter in [terraform/modules/dandiset_bucket/main.tf (expire_deleted_objects)](https://github.com/dandi/dandi-infrastructure/blob/master/terraform/modules/dandiset_bucket/main.tf#L310).

### dandi-schema
