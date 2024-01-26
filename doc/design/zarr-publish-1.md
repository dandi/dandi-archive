# Publish Dandisets with Zarr archives

This document describes the current implementation of publishing Dandisets with Zarr archives, a desired use case, and the associated requirements of this use case.

## Current implementation

Currently when a blob asset is updated, a new version (i.e. a copy) is uploaded to S3.  Zarr archives are too large so multiple copies should not be created.  A Zarr archive is uploaded once and it is edited in place.  This design means that the Zarr archive is immutable once the Dandiset is published.  For more details, see the [zarr-support-3 design doc](https://github.com/dandi/dandi-archive/blob/master/doc/design/zarr-support-3.md).

## Use case 1

Publish Dandisets with Zarr archive(s) following the general publishing procedure described in the [publish-1 design doc](https://github.com/dandi/dandi-archive/blob/master/doc/design/publish-1.md).  A modified publishing procedure that includes Zarr archive(s) is summarized below.

1. User uploads a new Dandiset which includes Zarr archive(s).
2. User uploads an updated Zarr archive in the `Draft` version of the Dandiset.  
3. User publishes the Dandiset and thereby creates a new version of the Dandiset.
4. User repeats steps 2 and 3.

## MVP Requirements (Target date: April 30, 2024)

1. Permit versioning of Zarr archives without creating a copy of the entire Zarr archive
1. Permit publishing of Dandisets with Zarr archives
1. Minimize storage costs in the design

## MVP+1 Requirements

1. Permit linking of a Zarr asset to multiple Dandisets - [dandi-archive/issues/1792](https://github.com/dandi/dandi-archive/issues/1792)


