# Versioned Zarrs

This document discusses the design of a *versioned Zarr* concept, which is needed to enable publishing of Zarr-bearing Dandisets.

Prior proposals:

- [`#1833`: Design doc - Publish Dandisets that contain Zarr archives](https://github.com/dandi/dandi-archive/pull/1833)
- [`#1892`: Design doc for Zarr versioning/publishing support via Zarr Manifest Files](https://github.com/dandi/dandi-archive/pull/1892)

## Executive Summary

Zarr Archives are simply too big and too complex to copy when modified to create new versions (as is done with “blob” assets). Instead, we propose to only change the stored objects for individual shards (in Zarr version 3) or chunks (in Zarr version 2), using S3 bucket versioning to maintain previous versions, while tracking the association between shard/chunk paths and S3 objects in a database table. This will enable a lightweight model representing an immutable snapshot of a Zarr Archive suitable for publishing in a Dandiset, as well as optimized access to the latest version of the Zarr, and other services such as Zarr manifest files.

Note: for simplicity, we will refer to the individual files comprising a Zarr, whether they are *chunks* or *shards* in context, as “chunks”. In particular, we wish to avoid the term “object” due to possible confusion with S3 objects. This proposal is unaffected by the difference between chunked and sharded Zarrs.

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

Note: the "latest Zarr" refers to the most recently finalized version of a Zarr. For instance, in a given Dandiset, an owner might upload Zarr (complete with a finalize operation). The system creates a versioned Zarr, `A`, with a suitable DANDI backend URL to identify it. At this moment, the associated S3 URL also points to this Zarr. Next, another owner uploads a new chunk (or makes other modifications to the Zarr), followed by another finalize operation; the system creates a versioned Zarr, `B`. Now, by necessity, the S3 URL points to `B` (since, for example, some of the chunks of `A` may have been removed or changed); the original DANDI backend URL for `A` still works, and there is a new DANDI backend URL for `B`, but the stable S3 URL now points to `B`. In that sense, the S3 URL associates to the "latest" version of the Zarr.

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

### Performance/Usability Tradeoffs

Requirement 4 (”a*ccess to the latest version of a Zarr via S3”*) forces the “archaeological” chunk storage strategy described above, with the benefit that the most recent version of a given Zarr will always be available via S3, providing performance benefits for consumers of the Zarr (no redirects from the DANDI API needed) and for administrators of the Archive (no incoming traffic to serve that Zarr).

However, this choice comes with downsides as well:

1. *Lack of optimization options for published Zarrs.* In short, because of the way the “archaeological” storage pattern works, published versions of Zarrs cannot be optimized for S3-only usage at all.
2. *Lack of general chunk deduplication for Zarrs.* The current design deduplicates Zarr chunks *per-Zarr*, and does not generalize to, e.g., the same chunks appearing in wholly different Zarrs, or the same Zarr being included in different Dandisets, etc.

A proposed alternative set of requirements would revoke the current Requirement 4, and replace it with the following:

1. **General chunk deduplication.** The Zarr upload logic will detect duplicate Zarr chunks in the same way as the asset upload logic currently does for asset blobs. Full, versioned Zarrs continue to be available via the DANDI Zarr backend API (which redirects requests to possibly deduplicated Zarr chunks stored in S3). Manifest files in S3 continue to provide clients with an alternate plan of access to those Zarrs (as in the proposed design).
2. **S3 materialization of Zarrs.** The archive administrators will be able to trigger *S3 materialization* of any version of a Zarr. To perform such a materialization, the system copies the chunks comprising a Zarr into an independent prefix, thus creating a copy of the Zarr that can be accessed directly from S3.

This proposal has the advantage of *engineering simplicity*, as it follows the existing approach of content-addressable deduplication of all uploaded assets, whether they are asset blobs or Zarr chunks. The main advantage is the ability to upload a large Zarr to multiple Dandisets (in the current design, doing so would kick off a new round of slow uploads, which may make this action practically unusable for very large Zarrs such as those found in Dandiset 108, and painful for many others). The main disadvantage is the loss of an implicit S3 view of the latest version of every Zarr.

Which design to choose hinges almost entirely on expected usage patterns of Zarrs in the Archive. For example, if the bulk of access to Zarrs occurs on the latest versions, then maintaining the latest version as an S3-accessible Zarr makes sense. If, on the other hand, Zarrs will be regularly replicated in different Dandisets (which might occur for a lab following the “one Dandiset per publication” rule), then optimizing for duplicated chunks makes sense.

Unfortunately, the two designs cannot coexist in order to serve two masters. Therefore, an evaluation of the downsides of each approach is in order. We refer to the design in the *Requirements* section above as “the proposed design”, while the alternative described in this section is “the alternate design”.

The main downside for the proposed design is continued UX pain in dealing with Zarrs: specifically, a lab that takes 30 days to upload a Zarr to a Dandiset, and understands that “DANDI deduplicates assets” may get a surprising violation of expectations when including that Zarr in a new Dandiset begins another 30 day upload cycle (and, in fact, will likely avoid the pain by seeking another route to constructing that Dandiset). Furthermore, any lab that does choose the pain will (needlessly) balloon the size of stored data in the DANDI Archive bucket. While the sponsored bucket means that will not incur extra costs, a non-sponsored project would indeed need to bear those costs. In addition, this approach also distorts the usage statistics presented on the front page. A second, but still significant downside concerns the engineering complexity alluded to above: the proposed design will be harder to implement, more prone to bugs, and very difficult to change later (should we decide to do so for any reason). Experience shows that such a downside should not be underestimated.

The downside for the alternate design is a heavier volume of request traffic to the DANDI API (that would otherwise go straight to S3), as well as possible performance degradation for the client, as those requests must now redirect to S3 to retrieve the actual chunks (incurring one extra “hop”).

The inability to use Zarrs as flexibly as other types of assets limits the usefulness of the Archive. Indeed, the power to freely re-upload Zarrs to different Dandisets at the amortized cost of a single actual upload opens the Archive to usage patterns that are simply not possible now (potentially helping to fulfill the DANDI project’s overall goals). Meanwhile, the performance gains from direct S3 access may be modest: experimentation with the `zarr-demo` instance has shown the performance cost of redirecting to S3 to be quite small (especially compared to the order of seconds sometimes required to retrieve the actual bytes from S3). Further performance testing can clarify initial results. The remaining downside to the alternate design is the ongoing need to maintain or scale extra web resources to handle possibly heavier Zarr traffic (especially in the case that the newly offered Zarr handling flexibility is popular with users, resulting in *more* Zarr uploads and activity). However, that might also be considered a sign of success, and therefore a welcome challenge.

Finally, Requirement 9 attempts to mitigate any such performance loss that may arise, by giving administrators an option to observe usage patterns per-Zarr, and materialize any particularly heavily used Zarr version as a dedicated, S3-available copy. This would work by making a static copy of all the chunks of that Zarr in a special prefix that can then be used as the official redirect target for that Zarr, or accessed directly by clients. (Manifest-driven access is unaffected by any of these considerations, and can continue to be used by special-purpose clients to avert excess traffic on the API.)

The crucial questions and discussion/investigation topics are the following:

1. **What are the expected and encouraged usage patterns for Zarrs?** In particular, can we confirm (with evidence, perhaps) that the heaviest-used Zarr will always by the latest version? Do we expect / plan to encourage people to share Zarrs between Dandisets?
2. **What are the performance characteristics of the DANDI API Zarr backend (compared to the S3 Zarr backend) and the manifest-driven access scheme?** If clients do not see a significant performance loss from using the DANDI Zarr backend (or if specialized clients can use manifest-driven access logic), then maintaining an S3 backend for every Zarr (at the costs described above) becomes less attractive for the overall system.
3. **What are the costs and benefits of the S3 materialization design?** The S3 materialization design attempt to bridge between the current proposal and this alternative proposal by still providing an avenue to hosting Zarrs in an S3 backend-compatible way.
