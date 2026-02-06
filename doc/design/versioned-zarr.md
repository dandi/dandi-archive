# Versioned Zarrs

This document discusses the design of a *versioned Zarr* concept, which is needed to enable publishing of Zarr-bearing Dandisets.

## Executive Summary

Zarr Archives are simply too big and too complex to copy when modified to create new versions (as is done with “blob” assets). Instead, we propose to only change the stored objects for individual chunks, using S3 bucket versioning to maintain previous versions, while tracking the association between chunk paths and S3 objects in a database table. This will enable a lightweight model representing an immutable snapshot of a Zarr Archive suitable for publishing in a Dandiset, as well as optimized access to the latest version of the Zarr, and other services such as Zarr manifest files.

## Current Situation

Zarr Archives (”Zarrs” for short) are a strategy for storing large multidimensional numeric array datasets in the cloud, optimized for parking data in a place one time, then bringing computation to it, rather than carting around such large amounts of data, which can be unwieldy, slow, and expensive. Conceptually, Zarrs consist of several “chunks” containing data or metadata and control information, organized into a standardized “folder” structure. The chunks may be thought of as “files” (particularly when a Zarr is stored on a filesystem), but the “files” and “folders” need not be literal files and folders, which in turn enables many “Zarr backends”, including systems that do not actually store folders and files (such as S3).

DANDI considers Zarrs to be a special type of asset, one that is not associated with an “asset blob” (i.e., a single file) but rather a specialized Zarr record that knows how to refer to an S3 prefix containing all of the chunks for that Zarr. Because Zarrs are large and complex, making a copy of the Zarr when it is updated (as is done for blob assets) is not feasible. This is essential to publishing a Dandiset, since a published version must contain an immutable set of assets (which may go on to be “edited” in copy-on-write fashion in future versions); as such, DANDI currently does not allow publishing of Zarr-bearing Dandisets.

This design offers a way of handling Zarrs that enables making lightweight snapshots of a Zarr Archive that are suitable for publishing.

## Requirements

1. **Lightweight snapshots of Zarr Archives.** The fundamental need for publishing of Zarr-bearing Dandisets is an immutable snapshot of a Zarr that does not involve a naive copying of all the objects the Zarr comprises.
2. **Publishing of Zarr-bearing Dandisets.** Once we are able to create lightweight Zarr snapshots, we will be able to update the publishing logic to enable published versions for Dandisets that contain Zarrs.
3. **Zarr backend for versioned Zarrs.** The Zarr snapshots will enable the DANDI API to act as a Zarr backend by redirecting requests for “paths” within the Zarr to the appropriate object in S3. This will enable applications expecting a Zarr to receive an appropriate DANDI API endpoint (and function equivalently to Zarrs hosted on S3, etc.); in particular, this opens the possibility for previous versions of Zarrs to be analyzed this way, even if there are active updates to that Zarr occurring simultaneously.
4. **Access to the latest version of a Zarr via S3.** As an optimization, the latest version of a Zarr will be available to access directly via S3. Under the assumption that most work on an evolving Zarr occurs at its cutting edge, making this version of the Zarr available via S3 avoids an excess burden on the DANDI API. Clients must be actively directed to this URL, rather than selecting a DANDI API URL that would bypass the optimization.
5. **Manifest files for Zarr versions.** When a Zarr snapshot is created and finalized, a manifest file containing information about the Zarr, including the associations between its chunk paths and corresponding S3 objects, must be published in S3. This manifest file serves as a valid snapshot of the Zarr, which clients can use to interact with it even as others are modifying the same Zarr to create newer versions thereof.
6. **CLI support for Zarr modification.** The DANDI CLI will need to perform appropriate analysis to communicate to the API local changes made to a Zarr in order to make use of the proposed infrastructure for versioned Zarrs.
7. **CLI support for Zarr download.** An optimization the CLI can offer would be to deal directly with Zarr manifest files when downloading or otherwise interacting with a Zarr. Currently, the CLI uses the DANDI API to download Zarr chunks; in this proposal, it could instead retrieve a manifest file and use that to drive its own logic around downloading the chunks, thus bypassing the API entirely (and sparing excess load on it).

## Proposals

### Zarr chunk storage

Zarr chunks will continue to be stored in the DANDI S3 bucket as normal (in particular, enabling S3 to continue serving as a Zarr backend for third-party applications). Whenever changes are made to a Zarr and it is then finalized, an additional step will occur to record the current makeup of the Zarr chunks as an immutable set of database rows mapping each chunk’s path to its versioned S3 object. As the Zarr continues to mutate, new such immutable snapshots will be produced; the latest such snapshot will become a permanent part of any published Dandiset. Garbage collection routines will work to clean up unreachable versions of Zarrs. As an example, consider a Zarr with the following chunks stored in S3 (listed with a notional version ID in parentheses):

- /zarr/foobar/.zattrs (0)
- /zarr/foobar/.zgroups (0)
- /zarr/foobar/0/0 (0)
- /zarr/foobar/0/1 (0)

Database rows tracking these four objects would comprise Version 0 of the Zarr:

- (0, .zattrs) → (/zarr/foobar/.zattrs, 0)
- (0, .zgroups) → (/zarr/foobar/.zgroups, 0)
- (0, 0/0) → (/zarr/foobar/0/0, 0)
- (0, 0/1) → (/zarr/foobar/0/1, 0)

Now imagine that a Dandiset owner modifies the Zarr by changing the data content of `0/0`, deleting `0/1` (for the sake of argument, even if that is not a realistic operation for a Zarr), and adding a new dimension’s worth of data in `1/0` and `1/1`, resulting in the following objects in S3 (with version *history* noted in parentheses):

- /zarr/foobar/.zattrs (0)
- /zarr/foobar/.zgroups (0)
- /zarr/foobar/0/0 (0, 1)
- /zarr/foobar/0/1 (0, D)
- /zarr/foobar/1/0 (0)
- /zarr/foobar/1/1 (0)

Once the Zarr is finalized, a new set of rows can be created as a snapshot of Version 1 of the same Zarr:

- (1, .zattrs) → (/zarr/foobar/.zattrs, 0)
- (1, .zgroups) → (/zarr/foobar/.zgroups, 0)
- (1, 0/0) → (/zarr/foobar/0/0, 1)
- (1, 1/0) → (/zarr/foobar/1/0, 0)
- (1, 1/1) → (/zarr/foobar/1/1, 0)

Note three things: first, that the view of the Zarr as it exists in S3 remains valid (reflecting the new Version 1 of the Zarr, and including the delete marker for the chunk at `0/1`); second, that the database rows for Version 1 reflect the same structure (specifically, that `0/0` now refers to Version 1 of the appropriate S3 object, and that no row appears for the deleted `0/1` chunk); third, that Version 0 of the Zarr is still available for use through the appropriate database rows, since the explicit object versions have been captured there as well.

### Versioned Zarrs and Dandiset publishing

A “versioned Zarr” can now be formulated as a database model that records some appropriate metadata about the Zarr archive, and contains links to the rows of the database table discussed above, thus aggregating all the chunks of that version of the Zarr (along with how to find the data objects in S3).

Changes to the publishing procedure for Dandisets will accommodate these versioned Zarr models, manufacturing appropriate Asset model instances that point to a versioned Zarr model to facilitate a published Dandiset version containing that Zarr.

### DANDI Zarr backend

Furthermore, a new DANDI API endpoint can now serve as a Zarr backend using the data described above. For a given versioned Zarr, an endpoint such as `/zarr/{id}/{version}/` would serve as the virtual root for chunks in the Zarr. A request such as `GET /zarr/{id}/{version}/0/1` would then redirect to the S3 chunk named in the database row for that Zarr, version, and chunk. Handing the endpoint to a third-party application would enable it to work with a specific version of a Zarr as it exists in, for example, a published Dandiset version.

The Zarr backend base URL will be discovered by asking the API for information about the Zarr; that response will contain a `location` that will be a DANDI API URL (for versioned Zarrs) or an S3 URL (for the latest, draft version of a Zarr). Giving the client this URL will, as previously noted, avoid excess burden on DANDI to provide redirects for each chunk.

### Zarr manifest files

Because versioned Zarrs are not usually available directly via S3 (since many of their chunks will be “buried” under more current versions of that object), maintaining manifest files for each version of a Zarr appearing in a published Dandiset maintains the structure of these Zarrs directly in S3 (similarly to the manifest files currently recording which assets belong to a published Dandiset). This preserves the integrity of the bucket itself as a standalone data store (independent of the DANDI API and web application), but also provides an optimization for clients.

Specifically, clients such as the DANDI CLI currently interact with Zarrs by asking the API for each chunk. For an operation such as “download a Zarr”, this can result in hundreds of requests per second to the API. However, if the CLI learned to first retrieve the manifest file, then issue requests directly to S3 to retrieve the chunks, all of the redirection burden is relieved (both for the API and the client itself).

### DANDI CLI changes

The CLI will need to update its logic to reflect the above proposals for how versioning of Zarrs will work. Specifically, it may need to compute a diff of sorts between Zarr archives on disk and the last version in the API; this diff can drive a series of changes requested to the API to update the appropriate objects making up a Zarr in S3. Together with changes to the server-side logic, the client will be able to process versioned Zarrs as well.

As mentioned in the previous section, the CLI may also learn to process published Zarrs by parsing the manifest file. This moves significant logic from the server to the client, but results in higher performance overall (the client retrieves chunks faster, and the API does not have to process a sustained volume of requests to redirect to S3). If this logic is valuable enough, it may be transferred into a standalone library (much as happened for `dandi-schema`).

## Other Approaches

### Icechunk

[Icechunk](https://icechunk.io/en/stable/overview/) is an open-source library that provides a similar service for Zarrs as those described in this document, plus many others designed to provide database-style safety guarantees for Zarr chunk storage. Integrating Icechunk with DANDI would likely be complexity and cost prohibitive due to its heavier nature, and its own unique schema for storing chunks. However, it remains an important point of comparison to DANDI’s approach.

### Standalone Web Service

A proposal to build the redirection logic into a standalone web service was raised, in order to overcome perceived difficulties of performance if many rows end up stored in DANDI’s Postgres database.

A quick sketch of this hypothetical service follows: as manifest files are published in the S3 bucket, the service would learn the association between individual Zarrs and their manifests. A user request to learn about a Zarr would result in the service retrieving that manifest and loading its contents into a cache (either in-memory, or using some attached service such as Redis). The user would query for chunk paths and receive S3 object URLs, just as in our proposal.

The perception of performance is that caching this data in memory would result in faster responses. However, this hypothetical service has many disadvantages against a system like Postgres. Specifically, its backing data store is S3, which is very slow to access compared to Postgres’s own data stores; it seeks to reinvent the core function of Postgres itself, but does not have the decades of experience and optimizations that Postgres does; and very specifically, the perception that an in-memory caching system for manifest files would be faster that Postgres fails against the bevy of multilevel caching strategies already employed by Postgres.

The recommendation is to implement the design using Postgres directly, and only consider other options if and when performance problems do arise.
