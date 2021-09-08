The Zarr format is being used by NGFF to support the next generation of microscopy data. This involves a potentially
nested folder structure with named files inside the folder. In the DANDI this would mean:

1. An asset is associated with a single zarr folder. From a user perspective this is still a single asset and the UI
   should not try to delve into the structure of the folder. The CLI should be able to download the entire tree. Matt
   at kitware is looking into IPFS + NGFF, so we should at least keep that in mind.
3. Blob store allows for a folder, which contains the zarr named "locations" and data. That is given a root prefix,
   a zarr-compliant software can navigate the zarr metadata/structure using relative path rules.
3. Blob url should continue to point to a single location (i.e. the prefix ending with `/` common to all keys for zarr files) in an s3 bucket instead of a collection of files.
4. The `etag` connected with the zarr file should be a tree-hash of dandi-etags of the folder.

Storing each sub-file of a zarr "dataset" as an asset seems like an overkill without any specific gain at this point.

Given these considerations here are questions for implementation
1. Is there a way to upload a folder to a given prefix using an API key without having to create 100k signed URLs?
1. Should the tree structure be stored somewhere so that diffs can be ascertained?
   * Assuming 64 bytes of checksum, 64 bytes for path (optimistic), and 1million files (pessimistic), that's 128MB of checksum info in the DB. Plausible for upload, but probably not long term.
1. Given that each zarr file may contain 100k+ files, how will dandi-cli handle alterations?

# Requirements

1. zarr files are stored in a "directory" in S3.
1. Each zarr file corresponds to a single Asset.
1. The CLI uses some kind of tree hashing scheme to compute a checksum for the entire zarr file. The API verifies this checksum _immediately_ after upload; it's not good enough to download the entire zarr file to calculate it after upload.
1. The system can theoretically handle zarr files with ~1 million subfiles, each of size 64 * 64 * 64 bytes ~= 262 kilobytes.

# Implementation

## Hash function for checksums
The hash function used to generate the checksum for the zarr file must have these characteristics:

1. It must be based on the dandi-etag function of the subfile contents, and the path of the subfile in the zarr file.
1. A well-defined ordering of the subfiles in the zarr file must exist.
The checksum must be computed on the subfiles in this order.
1. It must be applicable on one subfile at a time.
1. It must be able save its state between subfiles.

**TODO** what is this function?

A simple scheme that I think would work:

* initial value is `sha256("{etag}:{path}")` for the first subfile
* the next value is `sha256("{prev_sha256}:{etag}:{path}")`, ad infinitum

We could also do something more complicated with merkle trees or something, but it would be much more obnoxious to compute.

## Upload flow

### Before upload (technically optional)
1. CLI calculates the checksum of the zarr file.
1. CLI queries the API (**TODO** URL?) if the checksum has already been uploaded.
1. If so, it proceeds with the already uploaded zarr file and skips upload entirely.

### Upload
1. CLI queries the API (**TODO** URL?) with the checksum of the zarr file to initiate an upload. The API creates an upload UUID, records the checksum, and initializes a "running checksum" to `null`.
1. CLI requests a batch of presigned URLs (**TODO** URL?).
The files must be ordered in the same way used to calculate the checksum.
Any number of files may be requested in a batch.
The request body looks like this:
```
[
   {
      "path": "foo/bar.txt",
      "dandi-etag": "abc ... 123"
   },
   {
      "path": "foo/baz.txt",
      "dandi-etag": "def ... 456"
   },
]
```
3. API responds with a corresponding list of presigned upload URLs (**TODO** where to upload?) in the S3 bucket.
The size limit for each upload is 5GB.
The API also temporarily records the paths and ETags for later.
Any more requests for presigned URL batches will now fail until this batch has been completed.
3. CLI uses the presigned upload URLs to upload the files to S3.
3. CLI queries the API (**TODO** URL?) to inform it that all files have been uploaded.
No request body is included.
3. API looks up the paths + ETags and checks that there is a file in S3 for each path with the corresponding ETag.
If the ETag doesn't match, an informative error is returned (**TODO** how should the CLI deal with errors? abort the whole zarr upload? get new presigned upload URLs?).
If everything matches, the running checksum is augmented with each checksum in order.
In either case, unlock the presigning endpoint so that more files can be uploaded.
3. CLI repeats the upload process until the entire zarr file is uploaded.
3. CLI queries the API (**TODO** URL?) to finalize the upload. The API verifies that the final running checksum matches the checksum specified at the start of the upload process. The API creates a new `ZarrFile` that behaves basically like an `AssetBlob`.
3. CLI queries the API (`/dandisets/{versions__dandiset__pk}/versions/{versions__version}/assets/`) to create a new `Asset` using the freshly minted `ZarrFile`.

## Pros
* The CLI can throttle how big the presign batches are at will.
* Immediate, recoverable errors if any upload fails.
* AFAICT the only alternative that provides immediate checksum validation is to create a new service to proxy the entire upload process.
This approach involves substantially less network traffic on the API server.

## Cons
* Lots and lots of presigning.
Assuming 1 million subfiles and a batch size of 100, that's 10,000 presigning requests.
Honestly, not that unreasonable for this much data.
* The upload state is not saved, so no modifying upload history.
Because the checksum has a well-defined ordering, you cannot decide that you want to tack a few more files on at the beginning after you have begun the checksumming.
* Possibly inefficient hashing algorithm?
My approach was simple but possibly naive, maybe there's a better algorithm that meets the requirements.

## Benchmarks
I mocked up API endpoints that would behave more or less like the ones described above.
I recommend throwing the code away, but it should give a good estimate for performance.
See https://github.com/dandi/dandi-api/tree/zarr-demo, specifically https://github.com/dandi/dandi-api/commit/2e651e336a052f59e867ee97cca0f1c5b3e2ff2a for the code.

I ran these benchmarks locally against my local Minio object store.

Some sample logs from the benchmarking script:
```
Uploading 10000 files of size 20.000 KB, for a total size of 195.312 MB
Presigning 10000 URLs...
 1.256s
Uploading 195.312 MB of data direct to object store (this would be parallelizable)...
 67.029s
Verifying uploaded files are present in object store and have the correct ETag...
Upload complete!
 10.868s
```

The data:

| File Size | Total Size | Files | Presigning | Uploading | Verifying | Efficiency |
|---|---|---|---|---|---|---|
| 20KB | 20KB | 1 | 0.082s | 0.006s | 0.015s | 17.1% |
| 20KB | 200KB |10 | 0.014s | 0.050s | 0.024s | 56.8% |
| 20KB | 1.95MB | 100 | 0.025s | 0.581s | 0.270s | 66.3% |
| 20KB | 19.5MB | 1000 | 0.130s | 6.293s | 1.069s | 84.0% |
| 20KB | 195MB | 10000 | 1.256s | 67.029s | 10.868s | 84.7% |

Efficiency indicates what percentage of the total time taken was spent actually uploading bytes, as opposed to waiting for the server to presign or verify.
A direct upload to S3 would be 100% efficient.

These numbers are from uploading to my local Minio, so they omit the burden of actual network traffic.
However, uploading to S3 would involve network latency during the upload step and during the verification step, so the ratio should remain roughly the same.

Here is some data from connecting to an S3 bucket from my local machine (and associated wifi speeds):

| File Size | Total Size | Files | Presigning | Uploading | Verifying | Efficiency |
|---|---|---|---|---|---|---|
| 20KB | 20KB | 1 | 0.082s | 0.377s | 0.423s | 42.7% |
| 20KB | 200KB | 10 | 0.043s | 3.262s | 0.946s | 76.7% |
| 20KB | 1000KB | 50 | 0.104s | 15.134s | 3.677s | 80.0% |
| 20KB | 1.95MB | 100 | 0.077s | 30.912s | 6.901s | 81.6% |
| 20KB | 2.93MB | 150 | 0.095s | 46.975s | 10.614s | 81.4% |
| 20KB | 3.906MB | 200 | 0.117s | 61.827s | 14.048s | 81.4% |

The production ratio will hopefully be better, since the verification step involves requests to S3 from the Heroku API server, which is hopefully a better pipe than whatever wifi users are uploading from.

80% efficiency seems like a good estimate.
