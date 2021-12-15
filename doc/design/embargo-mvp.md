# Embargo Minimum Viable Product
Due to time constraints, we are implementing the core functionality for embargoing dandisets ASAP.
This document is dedicated to the minimum viable product.
A subsequent document will describe the full suite of features.


# User experience

## Web
When creating a new dandiset, users will have checkbox to choose whether or not the dandiset should be embargoed.
If so, the user must also specify an NIH award number (https://era.nih.gov/files/Deciphering_NIH_Application.pdf).
The award number is an optional argument that is passed to the create dandiset endpoint.
The award number will be added as a new `Funder` on an automatically generated Contributor Organization in the metadata.

Instead of the normal `Publish` button and version browser, the DLP will instead show a `Release` button.
Clicking it will open a confirmation modal informing the user that they are unembargoing, all their data will be publicized, there is no undoing, and that it can take some time for large dandisets.
Confirming will lock the dandiset for the duration of the release.
Once the release finishes, the dandiset will be like any other unpublished draft dandiset.

Once created, an embargoed dandiset is only visible or searchable to owners.
Instead of the `draft` chip, an `embargoed` chip should be used on the dandiset listing pages.
These dandisets+chips will only appear in the listings to owners of the embargoed dandisets.

## CLI
The CLI experience will be basically unchanged.
Uploads to an embargoed dandiset will function exactly the same from an API perspective, the data simply goes to a different location.

### TODO: how to browse/download embargoed zarr files?
Credentials need to be generated, distributed, and used by the client.


# Data storage
Embargoed assets will be stored in a separate S3 bucket.
This bucket is private and not browseable by the general public.

Each dandiset stored in the embargoed bucket will be prefixed with a dandiset identifier.
This will make it easier to manage embargo permissions for a specific embargoed dandiset.
The API server will use the embargo bucket to store blobs in exactly the same way it uses the public bucket, but with the embargoed dandiset prefixed.
Manifests will be stored at a different path to simplify redundant path information.

Assuming dandiset `123456` was embargoed:
* Blobs will be stored at `123456/blobs/123/456/123456...
* Manifests will be stored at `123456/manifests/...`
* Zarr files will be stored at `123456/zarr/{uuid}/...`

When releasing an embargoed dandiset, all asset data for that dandiset is copied to the public bucket.

When uploading a new asset to an embargoed dandiset, the server will first check if that blob has already been uploaded publically.
If so, the public blob will be used instead of uploading the data again to the embargo bucket.


# Django changes

## Models
The `Dandiset` model will have an `embargo_status` field that is one of `EMBARGOED`, `RELEASING`, or `OPEN`.
* `OPEN` means that the Dandiset is publically accessible and publishable.
  This is the state all Dandisets currently have.
* `EMBARGOED` means that the Dandiset is embargoed.
  It is not searchable or viewable to non-owners.
  It is not publishable.
  Manifest YAML/JSON files will be written to the embargo bucket rather than the public bucket.
* `RELEASING` means that the Dandiset is currently transitioning from embargoed to public.
  All modification operations will return a 400 error while the release is in progress.
  This includes metadata changes and uploads.

A new `EmbargoedAssetBlob` model will be added.
This behaves the same as a normal `AssetBlob`, but points to the embargo bucket rather than the public bucket.
It also contains a reference to the `Dandiset` it belongs to.

`Asset`s will point to exactly one `AssetBlob` or `EmbargoedAssetBlob`.
An `Asset` will be considered "embargoed" if it has an `EmbargoedAssetBlob`.
An embargoed `Asset` can only belong to the dandiset named in the `EmbargoedAssetBlob`.
The automatically populated `Asset` metadata will also set the `access` field to the appropriate value depending on whether or not the asset is embargoed.

The `Upload` model will have a new optional field `embargoed_dandiset` that points to an embargoed dandiset.
If specified, the uploaded data will be sent to the embargoed bucket instead of the public bucket, and the `Upload` will create an `EmbargoedAssetBlob` when finalized.

## API
* Create dandiset endpoint

  Add a new optional `award_number` field.
  If set, the `access` metadata field will be set to `EmbargoedAccess` and the award number will be recorded as a `Funder` on a new Contributor Organization.
  The `embargo_status` of the dandiset will also be set to `EMBARGOED`.

* Get/List dandiset endpoint

  The DandisetViewSet queryset will filter out dandisets with `embargo_status == EMBARGOED` that are also not owned by the current user.
  This will prevent them from showing up in the listing or fetching endpoints.

  The `DandisetSerializer` will also be updated to include the `embargo_status` field so that the web client can render the embargoed dandiset appropriately.

* publish version endpoint

  Return error 400 if `dandiset.embargo_status != OPEN`.

* create asset, update metadata, and any other dandiset/version modification endpoints:

  Return error 400 if `dandiset.embargo_status == RELEASING`.

* New endpoint: `POST /api/dandisets/{dandiset_id}/release`

  Release an embargoed dandiset.
  
  Only permitted for owners and admins. If the `embargo_status` is `OPEN` or `RELEASING`, return 400.

  Set the `embargo_status` to `RELEASING`, then dispatch the release task.

* Release task

  For every `Asset` with an `EmbargoedAssetBlob` in the dandiset, convert the `EmbargoedAssetBlob` into an `AssetBlob` by moving the data from the embargo bucket to the public bucket.
  These could be >5GB, so the [multipart copy API](https://docs.aws.amazon.com/AmazonS3/latest/userguide/CopyingObjectsMPUapi.html) must be used.
  The ETag and checksum must remain undisturbed; the only change should be where the data is stored.
  Verify that the resulting unembargoed assets match one-for-one (in the database) with the embargoed assets that were copied.
  Once finished, the `access` metadata field on the dandiset will be updated to `OpenAccess` and `embargo_status` is set to `OPEN`.
  
  Before copying data, check if an existing `AssetBlob` with the same checksum has been uploaded already (this would have happened after uploading the embargoed data).
  If so, use it instead of copying the `EmbargoedAssetBlob` data.

* Get/List asset endpoint

  The AssetViewSet queryset will filter out assets with `embargoed_asset_blob.dandiset.embargo_status != OPEN` that are also not owned by the current user.
  This will prevent them from showing up in the listing or fetching endpoints.

* upload_initialize_view

  An optional field `embargoed_dandiset` will be available on the serializer.
  If specified, it will be passed to the `Upload` object.
  This will mean the final upload will result in an `EmbargoedAssetBlob`.

  Even if `embargoed_dandiset` is specified, if an `AssetBlob` with a matching checksum already exists, return it instead of uploading embargoed data.
  This means that an embargoed dandiset can contain both embargoed and unembargoed assets.

  `EmbargoedAssetBlob`s should also be checked for deduplication, but only within an embargoed dandiset.
  This is to keep the permission model clean for owners of different embargoed dandisets that might contain the same asset.
  An embargoed dandiset should use the same `EmbargoedAssetBlob` if the same file appears in multiple places, but two embargoed dandisets should upload the same data twice if they both contain the same file.

  Return error 400 if `dandiset.embargo_status == RELEASING`.

* TODO zarr upload

* stats_view
  
  The total size value should include the size of `EmbargoedAssetBlob`s as well as `AssetBlob`s.