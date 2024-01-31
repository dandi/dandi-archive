# Publish Dandisets that contain Zarr archives, and support updates to the Zarr archive after publishing the Dandiset

This document describes the current implementation of publishing Dandisets with Zarr archives, desired use cases, and the associated requirements.

## Current implementation

When a blob asset is updated, a new version (i.e. a copy) is uploaded to the S3 bucket.  Zarr archives are too large so multiple copies should not be created.  A Zarr archive is uploaded once and it is updated in place.  This design means that the Zarr archive is immutable once the Dandiset is published, so that the published Dandiset is immutable. Currently, a Dandiset cannot be published if it contains a Zarr asset.  For more details, see the [zarr-support-3 design doc](https://github.com/dandi/dandi-archive/blob/master/doc/design/zarr-support-3.md).

## Use case 1

Publish a Dandiset containing a Zarr archive(s), and subsequently update the Zarr archive(s).

The publishing procedure would follow the description found in the [publish-1 design doc](https://github.com/dandi/dandi-archive/blob/master/doc/design/publish-1.md).  A modified publishing procedure that includes Zarr archive(s) is summarized below.

1. User uploads a new Dandiset which includes a Zarr archive(s).
2. User uploads an updated Zarr archive(s) to the `Draft` version of the Dandiset.  
3. User publishes the Dandiset and thereby creates a new immutable version of the Dandiset.
4. User repeats steps 2 and 3.

## Use case 2

Upload a Zarr archive to an embargoed Dandiset. 

## Use case 3

Reuse a Zarr archive in more than one Dandiset.

Allow for a Zarr archive that is uploaded as part of an original Dandiset to be packaged in a new Dandiset without duplicating the Zarr archive.  The new Dandiset could be created by potentially different authors and could contain additional raw and/or analyzed data.  This feature has been previously implemented for other asset types with [add_asset_to_dandiset.py](https://gist.github.com/satra/29404d965226e4c99fb48e7502953503#file-add_asset_to_dandiset-py).  Further details of this feature request have been previously documented in [dandi-archive #1792](https://github.com/dandi/dandi-archive/issues/1792).

## MVP User requirements (Target date: April 30, 2024)

1. Publish Dandisets that contain Zarr archives.
1. The published Dandisets must be immutable and accessible.
1. The draft version of the Dandiset should be mutable.
1. Minimize storage costs in the design.

## MVP+1 User requirements

1. Support linking of a Zarr asset to multiple Dandisets - [dandi-archive/issues/1792](https://github.com/dandi/dandi-archive/issues/1792)

## MVP Technical specifications

1. Support versioning of Zarr archives.
1. Create a unique web address for each published version of the Zarr archive.
1. Provide access to the Zarr archive versions through the web app and command line interface.
1. TODO: add additional specifications

## MVP+1 Technical specifications

1. TODO

## Potential solutions

1. Implement a Django backend for Zarr
    1. Stores data in a Postgres database that references the Zarr chunks in S3.

1. Earthmover's [Arraylake](https://earthmover.io/blog/arraylake-beta-launch)
    - Notes
        - Edits of the Zarr archive must happen through the Arraylake Python API, and thus the `dandi-cli` should be updated.
    - Questions
        - Egress costs?
        - Formal testing of Python API and infrastructure to ensure data integrity?

1. Create manifest file with paths and version IDs for each chunk for a specific version of the Zarr archive.
    1. Steps
        1. Initiate S3 bucket versioning
    1. Questions
        1. Store the manifest file in a database instead of S3 for improved performance?
    1. Constraints
        1. If the Zarr archive must be re-chunked then the user would need to upload the entire Zarr archive.
        1. Garbage collection would need to be updated.
