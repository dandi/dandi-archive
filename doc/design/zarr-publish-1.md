# Support updates to Zarr archives after publishing the corresponding Dandiset

This document describes the current implementation of publishing Dandisets with Zarr archives, a desired use case, and the associated requirements of this use case.

## Current implementation

When a blob asset is updated, a new version (i.e. a copy) is uploaded to the S3 bucket.  Zarr archives are too large so multiple copies should not be created.  A Zarr archive is uploaded once and it is updated in place.  This design means that the Zarr archive is immutable once the Dandiset is published, so that the published Dandiset is immutable. Currently, a Dandiset cannot be published if it contains a Zarr asset.  For more details, see the [zarr-support-3 design doc](https://github.com/dandi/dandi-archive/blob/master/doc/design/zarr-support-3.md).

## Use case 1

Publish a Dandiset containing a Zarr archive(s), and subsequently update the Zarr archive(s).

The publishing procedure would follow the description found in the [publish-1 design doc](https://github.com/dandi/dandi-archive/blob/master/doc/design/publish-1.md).  A modified publishing procedure that includes Zarr archive(s) is summarized below.

1. User uploads a new Dandiset which includes a Zarr archive(s).
2. User uploads an updated Zarr archive(s) to the `Draft` version of the Dandiset.  
3. User publishes the Dandiset and thereby creates a new immutable version of the Dandiset.
4. User repeats steps 2 and 3.

## MVP User requirements (Target date: April 30, 2024)

1. Publish Dandisets that contain Zarr archives.
1. The published Dandisets must be immutable and accesible.
1. The draft version of the Dandiset should be mutable.
1. Minimize storage costs in the design.

## MVP+1 User requirements

1. Support linking of a Zarr asset to multiple Dandisets - [dandi-archive/issues/1792](https://github.com/dandi/dandi-archive/issues/1792)

## MVP Technical specifications

1. TODO

## MVP+1 Technical specifications

1. TODO

