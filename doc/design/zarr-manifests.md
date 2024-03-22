Zarr Manifest Files
===================

This document specifies *Zarr manifest files*, each of which describes a Zarr
in the Dandi Archive, including the Zarr's internal directory structure and
details on all of the Zarr's *entries* (regular, non-directory files).  The
Dandi Archive is to automatically generate these files and serve them via S3.

@yarikoptic has already produced proof-of-concept manifest files for all Zarrs
in the Dandi Archive at <https://github.com/dandi/zarr-manifests>.  Except
where noted, the manifest file format defined herein matches the format used by
the proof of concept.


Creating & Storing Manifest Files
---------------------------------

Whenever Dandi Archive calculates the checksum for a Zarr in the Archive, it
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

The manifest file shall be world-readable, unless the Zarr is embargoed or
belongs to an embargoed Dandiset, in which case appropriate steps shall be
taken to limit read access to the file.

Manifest files shall also be generated for all Zarrs already in the Archive
when this feature is first implemented.


Manifest File Format
--------------------

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


Archive API Changes
-------------------

***WIP***

* Zarr version IDs equal the Zarr checksum

* Asset properties gain `zarr_version: str | null` field (absent or null if Zarr is not yet ingested or asset is not a Zarr)
    - Not settable by client
    - Mint new asset when version changes?

* Add `zarr_version` field to …/assets/path/ results

* Zarr `contentUrl`s:
    - Make API download URLs for Zarrs redirect to dandidav
    - Replace S3 URLs with webdav.{archive_domain}/zarr/ URLs?
        - Document needed changes to dandidav?
            - The bucket for the Archive instance will now be given on the command line (only required if a custom/non-default API URL is given)
            - The bucket's region will have to be looked up & stored before starting the webserver
            - Zarrs under `/dandisets/` will no longer determine their S3 location via `contentUrl`; instead, they will combine the Archive's bucket & region with the Zarr ID in the asset properties (templated into "zarr/{zarr_id}/")

* Getting specific Zarr versions & their files from API endpoints
    - `GET /zarr/versions/` (paginated)
    - `GET /zarr/versions/{version_id}/` ?
    - `GET /zarr/versions/{version_id}/files/[?prefix=...]` (paginated)
        - The Zarr entry objects returned in `…/files/` responses (with & without `versions/{version_id}/`) will need to gain a `VersionId` field containing the S3 object version ID
    - Nothing under /zarr/versions/ is writable over the API

* Publishing Zarrs: Just ensure that the `zarr_version` in Zarr assets is frozen and that no entries/S3 object versions from the referenced version are ever deleted ?

* Does garbage collection of old Zarr versions need to be discussed?
