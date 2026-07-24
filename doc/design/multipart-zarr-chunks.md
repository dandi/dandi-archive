# Multipart Upload for Zarr Chunks

For simplicity, and under the assumption that it would be sufficient, the DANDI Archive supports only single-part upload for Zarr chunks: Zarr archives, by design, store massive amounts of data in a large number of small files, and we predicted that no Zarr chunk would ever need to be as large as 5GB (the single-part upload size limit for S3). However, recently a lab did have a need to break this limit. This document describes a minimally disruptive design for supporting multipart upload for Zarr chunks, skirting the 5GB chunk-size limit.

## Requirements

1. **The Zarr system must support chunks of greater than 5GB.** This straightforwardly solves the original problem, but necessarily requires switching to multipart upload.
2. **The CLI must learn a new checksumming algorithm.** Because some Zarrs pre-exist this change with single-part chunks, and new uploads will create multipart chunks, the checksumming algorithm used for detecting changes in Zarr archives must adapt to the different strategies for uploading chunks.
3. **Checksum performance must not degrade significantly from its current baseline.** Implementation strategies may have impacts on performance; we need to ensure that in particular the CLI’s checksumming routines operate at roughly the same performance level as it currently does in order to preserve user experience.

## Implementation Sketch

### DANDI Backend

The basic idea is to tag Zarr Archive objects with a boolean `multipart` flag that indicates how the chunks in it were uploaded. In practical terms, all existing Zarrs would have this set to `false`, while all newly created Zarrs would have it set to `true`. This flag then governs how upload is carried out for the chunks: for `multipart=true`, the client will initiate a multipart upload by `POST`ing to an initialization endpoint, then the server will generate the same sequence of presigned URLs as it currently does for blob upload, the client will use them to upload a chunk by parts, followed by the client `POST`ing to a completion endpoint.

For existing (`multipart=false`) Zarrs, the upload procedure remains the same as it is now, enabling the client to upload single-part chunks only.

## DANDI CLI

The CLI will require two changes. For its uploading procedure, it will need to query the Zarr Archive’s `multipart` flag; depending on the value, it will either engage in a single-part upload (for `false`) as it does now, or it will branch onto a path where it initiates a multipart upload and performs one or more `PUT` operations to the presigned part URLs coming from the server.

For its checksumming procedure, it will check the `multipart` flag; for `false`, it uses the same checksumming algorithm as it does now (using whole-object md5 sums for each chunk, composing them into a tree of hashes, then hashing the whole thing). For `true`, it will change its approach to compute S3’s part-based pseudo-md5 sum for each chunk (taking into account a hash for each part, then hashing the concatenation of those before appending the number of parts to that string), following the same hash-of-hashes strategy to compute the checksum for the entire Zarr.

## Limitations and Tradeoffs

This design removes limits on the size of Zarr chunks by ensuring that multipart upload is used for all uploads to Zarrs created in the future. It does not allow for uploading 5GB+ chunks to *existing* Zarrs, for two reasons: first, supporting a fully hybrid single-part/multipart Zarr chunk mix would require consulting the server for the etag of every chunk every time the client wants to compute a checksum, which would catastrophically degrade the performance of that operation; second, it is unlikely that existing Zarrs will need 5GB+ chunks added to them (even the lab that needed this feature decided to re-chunk their offending Zarr and was able to use single-part uploads).

If someone truly needs to hybridize an existing, non-multipart Zarr with multipart chunks, there are some workarounds:

1. **Reupload the entire Zarr.** Reuploading the Zarr would make use of the new multipart architecture, enabling large chunks and avoiding the need for hybridized-chunk Zarr support.
2. **Introduce a `mixed` multipart modality.** If reuploading the Zarr is prohibitive, we can imagine a `mixed` mode that incurs the performance penalty described above. For Zarrs with many parts, the overwhelming number of requests to verify each checksum’s multipartness (by asking S3 for the etag value and examining it for a trailing part number) may become intolerably slow. We could warn the user about this situation, but it introduces other weaknesses, chief among them complexity: attempting to correctly implement a mixed-mode algorithm will likely run into edge and corner cases that are likely to lead to bugs and possibly data loss.

## Reference Implementation

This design has been implemented in PR #???
