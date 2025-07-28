# Asset Garbage Collection

## Background

Now that the [design for asset blob and upload garbage collection](./garbage-collection-uploads-asset-blobs-2.md) is deployed to staging, we are ready to implement Asset garbage collection. The garbage collection process in this design document only applies to “regular” assets; garbage collection of zarrs is not covered and is out of scope for this design doc.

## What is an “Orphaned Asset”

It’s important to precisely define what it means for an asset to be eligible for garbage collection (an “orphaned asset”).
An orphaned asset has the following properties:
- The asset is not currently associated with any Versions
- The asset is older than 30 days

## Integration with existing garbage collection routines

Garbage collection routines for Asset Blobs and Uploads are already implemented and deployed (though not run yet). Currently, the number of Asset Blobs and Uploads that need to be garbage collected is not substantial. However, the act of running the Asset garbage collection routine will result in a significant amount of Asset Blobs being orphaned, which can then in turn be collected by the Asset Blob garbage collection routine.

## Implementation notes

A new module, `asset`, will be added to the `garbage_collection` service (see `../dandiapi/api/services/garbage_collection/`). This module will mirror the structure of the sibling `asset_blob` and `upload` modules and will be responsible for deleting orphaned assets and handling associated recordkeeping (i.e. adding a record to the `GarbageCollectionEvent` table for every delete event).

We will introduce the feature initially by making it manually runnable via `manage.py collect_garbage` . This script [already exists](https://github.com/dandi/dandi-archive/blob/master/dandiapi/api/management/commands/collect_garbage.py) and currently supports asset blob and upload garbage collection, so it’s just a matter of integrating the `garbage_collection.asset` module into it once it’s implemented. Additionally, the script supports a dry run mode where it will log the number of items to be garbage collected, but not actually perform the delete operations. Once we’ve run it in production a few times and we’re ready, we’ll automate it with a cron via a Celery Beat task that calls the relevant service functions.

As is the case with asset blobs and uploads, an orphaned asset will remain recoverable by DANDI Archive admins for 30 days after it is garbage collected.

## Data

The current amount of orphaned data in the system as of 6/30/25 is as follows:

- Assets: 278,186 (335,356.39 GB)
- AssetBlobs: 103 (385.52 GB)
- Uploads: 1040 (0.01 GB)

**Note that about 336 TB out of the approximately 1.2 PB currently in DANDI (as of 6/30/25) consists of orphaned Assets and will be garbage collected.**

Note, the "total data size" on https://dandiarchive.org/ currently excludes orphaned assets and will not change as a result of garbage collection.

## Implementation

See https://github.com/dandi/dandi-archive/pull/2368 for the implementation of this design.
