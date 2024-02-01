# Discussion on metadata needed for dandidav

Submitted as a PR to avoid spagetti thread discussion on https://github.com/dandi/dandi-archive/issues/1837#issuecomment-1921864949


@jwodder listed needed properties and metadata fields:

* Asset properties used by dandidav:
    * `asset_id` (PRESENT)
    * `blob_id`
    * `zarr_id`
    * `path` (PRESENT)
    * `size`  (PRESENT)
    * `created` (GOOD TO HAVE)
    * `modified` (SUGGESTED to be included)
        * Note: It might be more accurate to use the `blobDateModified` metadata field for this instead; cf. dandi/dandidav#17

* Asset metadata used by dandidav:
    * `encodingFormat` (blobs only) (STRONGLY DESIRED but not REQUIRED)
    * `contentUrl` (API download URL for blobs, S3 URL for Zarrs) (INCLUDED)
    * `digest["dandi:dandi-etag"]` (blobs only)
