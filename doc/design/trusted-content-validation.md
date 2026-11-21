# Trusted File and Dataset Validation

Authors: Cody Baker

Status: proposal

This is the overview of the design. [Trusted File and Dataset Validation: Details](trusted-validation-details.md) specifies each change.

# Contents

- [Terminology](#terminology)
- [Flow](#flow)
- [Overview](#overview)
  - [Goals](#goals)
  - [Summary](#summary)
- [Proposed solution](#proposed-solution)
  - [Publication latency (accepted trade-off)](#publication-latency-accepted-trade-off)
  - [Old files vs. new checks (accepted trade-off)](#old-files-vs-new-checks-accepted-trade-off)
- [Proposed Rollout Order](#proposed-rollout-order)
- [Alternatives to consider](#alternatives-to-consider)
- [Open questions](#open-questions)

# Terminology

- **Validator versions:** the exact versions of the six packages that affect validation results: dandi, dandischema, nwbinspector, pynwb, hdmf and bids-validator-deno. For example (the versions here and below are illustrative):

  ```json
  {"dandi": "0.75.0", "dandischema": "0.12.0", "nwbinspector": "0.7.1", "pynwb": "3.1.0", "hdmf": "4.1.0", "bids-validator-deno": "2.1.0"}
  ```

- **Version code:** a short, readable string form of validator versions: each package's one-letter code followed by its version, joined by `-`. For the map above: `d0.75.0-s0.12.0-n0.7.1-p3.1.0-h4.1.0-b2.1.0`. It is the validator image's tag and part of each record's path in the bucket (see [Validator versions](trusted-validation-details.md#validator-versions) for the exact format).
- **Worker:** a separate Heroku app that runs the validator image, claims validation jobs from the archive, and reports their results.
- **Record:** the full output of one validation run, listing every error, warning and hint, stored in the archive bucket with its provenance. A summary of it goes in the database.
- **Validation target:** the version code of the newest validator image a worker has reported (see [Version updates](trusted-validation-details.md#version-updates)).
- **Required versions:** the version code a draft must be validated with: the validation target at the draft's last file change (see [Required versions](trusted-validation-details.md#required-versions)).
- **Content fingerprint:** a hash of the files a version contains, updated in constant time whenever an asset is added, removed or replaced (see [Content fingerprint](trusted-validation-details.md#content-fingerprint)).
- **Gating and shadow mode:** with gating on, the archive blocks publication unless the result passed. With a worker running and gating off (shadow mode), results and the banner appear, but publication is not gated.

# Flow

How a new validator release and a change to a draft's files flow through the system.

```mermaid
flowchart TD
    subgraph scan["Daily version scan (GitHub Actions)"]
        S1["Check PyPI for new validator releases"] --> S2{"New combination of versions?"}
        S2 -- no --> S3["Stop"]
        S2 -- yes --> S4["Build, test and release a new validator image"]
    end

    subgraph archive["dandi-archive"]
        A1["Owner adds, removes or replaces assets"] --> A2["Record the new content and move the draft to the current validator versions"]
        A2 --> A3["Queue a validation job once every file's checksum is known"]
        M1["Owner edits metadata only"] --> M2["Content unchanged: keep the validator versions and result"]
        T["Validation target: the newest validator image a worker has reported"]
        A7["Store the result and record pass or fail in the draft's metadata"] --> A8{"Passed?"}
        M2 --> A8
        A8 -- yes --> A9["Publishing allowed"]
        A8 -- "failed or not run yet" --> A10["Publishing blocked; banner shows the status"]
    end

    subgraph worker["Validation worker (Heroku container app)"]
        W1["Claim a job, reporting the image's version code"] --> W2["Validate the whole Dandiset with dandi validate, streaming files instead of downloading them"]
        W2 --> W3["Upload the full record and report a summary"]
    end

    S4 -. new image .-> W1
    W1 -. reports code .-> T
    T --> A2
    A3 --> W1
    W3 --> A7
```

# Overview

## Goals

- A Dandiset version cannot be published unless a trusted validation record for its current content contains no errors.
- The record must come from an exact, known set of validator versions:
  - **Drafts:** the validation target at the draft's last file change (an asset added, removed or replaced). Metadata-only changes, including to Dandisets already published, don't move it.
  - **Published versions:** the set frozen at publication, which is only possible if the version was valid then, so later validator releases never make them invalid.
- Errors and warnings are shown to everyone in a banner on the Dandiset landing page ([#1486](https://github.com/dandi/dandi-archive/issues/1486)). Warnings do not block publication but reflect overall quality. Only `ERROR` and `CRITICAL` results block (see [Validation job](trusted-validation-details.md#validation-job)).

## Summary

Today the archive only validates simple asset-level metadata: each Asset's metadata is compared against the `PublishedAsset` schema, and the draft Version's metadata against the `PublishedDandiset` schema (see [Current state](trusted-validation-details.md#current-state)).

Neither the archive backend nor any external service runs the validators that check the *contents* of files nor the *layout* of datasets: NWB Inspector, PyNWB validation, BIDS validator, or even the ad-hoc DANDI layout enforced by CLI command `dandi validate`. As a result, Dandisets with invalid NWB files or BIDS/DANDI layouts can be published (e.g. [#2412](https://github.com/dandi/dandi-archive/issues/2412)).

This document proposes running `dandi validate` over every draft Dandiset in a dedicated validation worker: a separate Heroku app that runs a container image. After a draft's asset manifests are written, the archive queues a job, and the worker claims it, builds a DataLad dataset from the version's assets and streams validation through dandi-cli's datalad-fuse support ([dandi/dandi-cli#1955](https://github.com/dandi/dandi-cli/pull/1955), [#1956](https://github.com/dandi/dandi-cli/pull/1956)). This approach simplifies the majority of modifications that would be required to both the BIDS-Validator and the NWB Inspector to adapt them away from filesystems (even symlinked 'mock' ones as DataLad creates).

- **Results:** each draft Dandisets metadata gets two new fields: the exact validator versions its result must come from (corresponding generally to the 'latest' at time of last asset modification), and whether that result passed or failed (with detailed JSON record of all errors, warnings, etc.). A summary of each result goes in a new table, and the full record goes in the archive bucket.
- **Gating:** the archive blocks publication unless that result has no errors.

The changes in each repository can be summarized as:

| Repository | Change |
|---|---|
| [dandi-schema](trusted-validation-details.md#dandi-schema) | A `ValidatorType` enum, two read-only `Dandiset` fields, one publication rule, one schema version bump |
| [dandi-archive](trusted-validation-details.md#dandi-archive) | One table, a small job API for the worker, a reconciler task, new `Version` columns with a one-off backfill, a daily image-build workflow, the worker's container image, a few lines in draft validation and publishing, `/versions/{version}/info/` fields, a banner, a daily check |
| [dandi-infrastructure](trusted-validation-details.md#dandi-infrastructure) | A new Heroku container app for the worker, and config vars on both apps |
| [dandi-cli](trusted-validation-details.md#dandi-cli) | A release with the streaming stack and small fixes |
| [datalad-fuse](trusted-validation-details.md#dandi-cli) | A release with the remfile backend, so dandi-cli can depend on it |

# Proposed solution

The main decisions are:

- **Gating through the schema.** dandischema gains two read-only `Dandiset` fields: `validatedRequiredVersions` and `validatedBy` (`null` when not run yet, `false` when failed, `true` when passed). Its publication check requires `validatedBy: true` whenever `validatedRequiredVersions` is set, so the archive's existing publish gating blocks publication without a new check in the publish service (see [dandi-schema](trusted-validation-details.md#dandi-schema) and [Stamping](trusted-validation-details.md#stamping)).
- **An isolated worker.** The worker holds no database, bucket or Django credentials: it claims jobs through a small job API, reads files through URLs the archive hands out, and uploads records through presigned URLs (see [Validation worker app](trusted-validation-details.md#validation-worker-app) and [Job API](trusted-validation-details.md#job-api)).
- **Automatic validator updates.** No validator version or image is committed anywhere. A daily scan builds and releases an image for each new set of PyPI releases, failing with an alert on any version that isn't a plain `MAJOR.MINOR.PATCH` release, and the archive targets the newest image its workers report (see [Version updates](trusted-validation-details.md#version-updates)).
- **Whole-Dandiset runs.** A file's result can depend on other files, so results aren't cached from one job to the next, and every run validates the whole Dandiset (see [No caching across jobs](trusted-validation-details.md#no-caching-across-jobs)).
- **Results tied to content.** Each result is stored with the content fingerprint and version code it was produced for, so a draft is validated again only when its files change (see [Content fingerprint](trusted-validation-details.md#content-fingerprint) and [Required versions](trusted-validation-details.md#required-versions)).
- **Everything kept.** Summary rows and bucket records are never deleted, and each run keeps its own record (see [Summary table](trusted-validation-details.md#summary-table) and [Record storage](trusted-validation-details.md#record-storage)).
- **What owners see.** After a file change, the landing page shows that validation is queued or running, with its progress. Once gating is on, publishing waits for the result: a pass enables it, and errors block it. Errors and warnings are counted in a banner and listed in the existing validation dialog, and fixing the files starts a new run. Metadata-only edits keep the existing result and start no run. If a run cannot complete, staff are notified and can re-run it, or override a result they judge a false positive, which updates the draft's status (see [Frontend](trusted-validation-details.md#frontend) and [Management commands](trusted-validation-details.md#management-commands)).

## Publication latency (accepted trade-off)

After a content change, the owner can publish only once the worker has validated the new content: the queue wait plus a full validation of the Dandiset. Embargoed drafts are validated too, and their record carries over at unembargo because the fingerprint doesn't change, so publishing right after unembargo is not delayed. This delay is accepted in exchange for publishing only validated content.

Because every run validates the whole Dandiset, adding one file to a very large Dandiset means re-validating all of it, and a run longer than a day cannot finish on Heroku, whose dynos restart daily. The pilot measures this (see the "Large Dandisets" [open question](#open-questions)).

To notice a stalled worker, a daily email tells developers about every draft that has waited more than three days for a result (see [Monitoring](trusted-validation-details.md#monitoring)).

## Old files vs. new checks (accepted trade-off)

Once a draft's files change, the whole Dandiset is validated with the latest validation target, so files carried over from earlier releases are re-checked with the latest validators. A small content change, such as adding one file, could therefore be blocked by a check that did not exist when the other files were published. This is accepted, because it means content and structure enhancements go hand-in-hand. Metadata-only changes are unaffected (see [Required versions](trusted-validation-details.md#required-versions)).

# Proposed Rollout Order

[Rollout details](trusted-validation-details.md#rollout-details) gives the specifics of each step.

1. **dandi-schema:** release the schema changes.
2. **datalad-fuse:** release the remfile backend.
3. **dandi-cli:** release the streaming stack and fixes.
4. **dandi-infrastructure:** add the worker app, with no dynos running yet, staging first.
5. **dandi-archive:** ship the archive changes and the daily version scan, with gating off.
6. **Pilot:** test the whole flow on staging, and measure the cost on a small, a BIDS and a large production Dandiset by running the image outside the archive. Then choose the worker's dyno size and count.
7. **Shadow mode:** start the production worker. Its first claim sets the target and queues every draft, which starts step 8.
8. **Sweep** every draft (see the "Sweep capacity" [open question](#open-questions)).
9. **Review:** when the majority of records are available, review them for accuracy and summarize potential effects and performance.
10. **Turn gating on**, after telling the owners whose drafts the review found would be blocked.

# Alternatives to consider

- **A dedicated publish check in the archive instead of a schema rule.** This would need changes to `Version.publishable` and `_lock_dandiset_for_publishing`, a new exception, and frontend gating, all of which the schema rule reuses. The schema rule also makes the requirement visible to anyone validating DANDI metadata.
- **An external trusted runner (the previous design).** A runner on separate compute would validate the `dandisets/` DataLad clones and push summaries through a staff-only endpoint. It was not chosen because the backup lag adds publication latency and it cannot read embargoed content. The chosen design keeps its isolation, but takes its inputs from the archive.
- **Validators inside the archive app.** Running the validators as a subprocess on a worker dyno of the archive's own app avoids a second app and the job API. But that dyno holds the database, bucket and Django credentials, and it must carry every validator environment.
- **Store full records in the archive database.** They are large, and it would tie the archive to dandi-cli's record model, which rejects unknown enum values.
- **A richer provenance object**, e.g. a `ValidationActivity(Activity)` with `Software` entries in `wasAssociatedWith`, mirroring `publishedBy: PublishActivity`. It is more expressive, but the map and boolean are simpler to look up and to enforce in `check_publication_status`.

# Open questions

1. **Sweep capacity.** Should workers on HPC, running the same image, join the worker app for the initial sweep?
2. **Large Dandisets.** A run longer than a day cannot finish on Heroku, whose dynos restart daily. Options include sending large jobs to workers elsewhere (e.g. on HPC), a Heroku time limit under a day, and parallelism within a job. To be decided from the pilot.
3. **Retry thresholds.** How many retries, and how much backoff, before a run is marked failed?
4. **Zarr.** Every asset should be NWB or BIDS, and either can be stored as Zarr. Zarr-backed assets are reported as "not checked" for now, and Dandisets containing Zarr [can't be published](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/publish/__init__.py#L64-L65) today. Should validation include them? Including them would also require adding each Zarr's checksum to the version's asset listings.
