# Publish Dandisets with Zarr assets

This document describes the current implementation of publishing Dandisets with Zarr assets, a future use case, and the associated requirements.

## Current implementation

Currently when a blob asset is updated, a new version (i.e. a copy) is uploaded to S3.  Zarr assets are too large to create multiple copies, so the upload occurs once and it is edited in place.  This design means that the Zarr archive would be immutable once published.  So currently the system is designed to not publish Dandisets that contain Zarr asset(s).

## Use case 1

Publish Dandisets with Zarr asset(s) following the general publishing procedure described in the [publish-1 design doc](https://github.com/dandi/dandi-archive/blob/master/doc/design/publish-1.md).

### Steps

1. User uploads a new Dandiset which includes Zarr asset(s).
2. User uploads an updated Zarr asset in the `Draft` version of the Dandiset.  
3. User publishes the Dandiset and thereby creates a new version of the Dandiset.
4. User repeats steps 2 and 3.

## MVP Requirements (Target date: April 30, 2024)

1. Permit versioning of Zarr archives without creating a copy of the entire Zarr archive
1. Permit publishing of Dandisets with Zarr assets
1. Minimize storage costs in the design

## MVP+1 Requirements

1. Permit linking of a Zarr asset to multiple Dandisets - [dandi-archive/issues/1792](https://github.com/dandi/dandi-archive/issues/1792)


- Zarrbargo - Zarr interacts with embargo.  Hide and unhide for all subfiles.
- Copy on write happens because of publishing
- Zarr related copies, copies on writes

