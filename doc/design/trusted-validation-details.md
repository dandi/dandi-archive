# Trusted File and Dataset Validation: Details

Authors: Cody Baker

Status: proposal

This document specifies the changes proposed in [Trusted File and Dataset Validation](trusted-validation.md), which gives the goals, terminology, flow and trade-offs.

# Contents

- [Current state](#current-state)
- [Validator versions](#validator-versions)
- [Proposed solution](#proposed-solution)
  - [dandi-schema](#dandi-schema)
  - [dandi-archive](#dandi-archive)
    - [Content fingerprint](#content-fingerprint)
    - [Required versions](#required-versions)
    - [No caching across jobs](#no-caching-across-jobs)
    - [Settings](#settings)
    - [Summary table](#summary-table)
    - [Triggering](#triggering)
    - [Job API](#job-api)
    - [Validation job](#validation-job)
    - [Validation worker app](#validation-worker-app)
    - [Validator image](#validator-image)
    - [Version updates](#version-updates)
    - [Record storage](#record-storage)
    - [Stamping](#stamping)
    - [Publication](#publication)
    - [Read API](#read-api)
    - [Frontend](#frontend)
    - [Search](#search)
    - [Management commands](#management-commands)
    - [Monitoring](#monitoring)
  - [dandi-infrastructure](#dandi-infrastructure)
  - [dandi-cli](#dandi-cli)
- [Lifecycles](#lifecycles)
- [Rollout details](#rollout-details)

# Current state

These are the parts of the archive this design builds on. Links point to dandi-archive and dandi-infrastructure `master` at the time of writing.

- **Version status and publishing.** [`Version.status`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/models/version.py#L57) reflects *Dandiset metadata* validation only. [`Version.publishable`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/models/version.py#L93-L102) requires `status == VALID` and every asset `VALID`, and [`_lock_dandiset_for_publishing`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/publish/__init__.py#L67) refuses to publish otherwise.
- **Draft validation is publish-time validation.** [`validate_version_metadata`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/metadata/__init__.py#L119) does three things:
  - it [builds](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/metadata/__init__.py#L127) the would-be published metadata with [`_build_publishable_version_from_draft`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/publish/__init__.py#L91-L115), which injects `datePublished` and `publishedBy`;
  - it [validates](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/metadata/__init__.py#L154-L158) that metadata against `PublishedDandiset`;
  - it [stores](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/metadata/__init__.py#L200) the outcome in `Version.status` / `Version.validation_errors`.

  Any rule dandischema enforces on *published* Dandisets therefore already marks the draft `INVALID`. That blocks re-publishing at a later time, and the UI shows the error in its existing validation dialog.
- **When validation runs.** Every change to a draft sets it to `PENDING`: [adding](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/asset/__init__.py#L83-L85) or [removing](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/asset/__init__.py#L96-L98) assets, [editing metadata](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/views/version.py#L126), [unembargoing](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/embargo/__init__.py#L71) and [Zarr ingestion](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/zarr/tasks/__init__.py#L89-L91). A beat job, [`validate_draft_version_metadata`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/tasks/scheduled.py#L91-L107), runs every [`DANDI_VALIDATION_JOB_INTERVAL`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/settings/base.py#L219) seconds and queues metadata validation, the assets summary, and `write_manifest_files` for it. Publishing also [writes manifests](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/publish/__init__.py#L208) for the new published version.
- **Checksums arrive later.** A new blob's `sha256` is computed later by [`calculate_sha256`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/tasks/__init__.py#L36-L43) on the [`checksum-worker`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/Procfile#L11) dyno, and asset validation [waits for it](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/tasks/scheduled.py#L68-L78). When the asset then validates, the draft's `modified` [is bumped](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/metadata/__init__.py#L86), but the draft is not set back to `PENDING`.
- **Publishing copies the draft's metadata.** `_build_publishable_version_from_draft` [deep-copies](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/publish/__init__.py#L93) the draft's metadata into the new published Version. Published metadata is immutable.
- **Server-computed fields** such as `assetsSummary` are removed from user-supplied metadata by [`Version.strip_metadata`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/models/version.py#L185-L201).
- **Dynos.** The [`Procfile`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/Procfile) defines [`web`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/Procfile#L2), [`worker`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/Procfile#L4-L9) (the default queue, which also runs beat, so its tasks must stay lightweight) and [`checksum-worker`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/Procfile#L10-L11).
- **Bucket.** Objects are [publicly readable](https://github.com/dandi/dandi-infrastructure/blob/6b79cf5a76ffd776b9d553d61ac5b9366ce3d39c/terraform/modules/dandiset_bucket/main.tf#L144-L159) except [those tagged `embargoed=true`](https://github.com/dandi/dandi-infrastructure/blob/6b79cf5a76ffd776b9d553d61ac5b9366ce3d39c/terraform/modules/dandiset_bucket/main.tf#L161-L186), and the archive's IAM user [can read embargoed objects too](https://github.com/dandi/dandi-infrastructure/blob/6b79cf5a76ffd776b9d553d61ac5b9366ce3d39c/terraform/modules/dandiset_bucket/main.tf#L178-L185). Under `dandisets/`, a [lifecycle rule](https://github.com/dandi/dandi-infrastructure/blob/6b79cf5a76ffd776b9d553d61ac5b9366ce3d39c/terraform/modules/dandiset_bucket/main.tf#L309-L323) keeps only the newest noncurrent version of each object and deletes older ones after a day.

# Validator versions

[Terminology](trusted-validation.md#terminology) defines validator versions and the version code.

- **Keys:** plain distribution names, and all six are always present.
- **Source:** all six versions are read from the validator image that produced the record (see [Validator image](#validator-image)). `dandischema` here is that image's dandischema, not the archive's own dandischema library or the metadata's `schemaVersion`.
- **Sanity check:** every result whose origin is one of these validators carries the image's version of it as `origin.validator_version`. hdmf produces no results of its own, so its version is recorded alongside pynwb's (see [dandi-cli](#dandi-cli)).
- **Order:** a version code lists the packages in the fixed order of `VALIDATOR_CODES` below, so equal maps always give identical codes.
- **Plain releases only:** every version must be a proper semver `MAJOR.MINOR.PATCH` release made only of digits and periods (e.g. `0.75.0`). Together with the single-letter codes, this keeps `-` out of every entry, so a code is unambiguous. Anything else, such as a pre-release, dev or local version (e.g. `1.0rc1`, `0.75.0+12.gabc`) or a different number of parts, is rejected with an error naming the package and version.

<details>
<summary>Implementation</summary>

A dependency-free module in dandi-archive, used by both the archive and the worker image, holds the code table and two helpers that build and parse version codes:

```python
#: One-letter code of each validator distribution in a version code, in the code's order
VALIDATOR_CODES = {
    "dandi": "d",
    "dandischema": "s",
    "nwbinspector": "n",
    "pynwb": "p",
    "hdmf": "h",
    "bids-validator-deno": "b",
}
```

- **Building** a code from resolved versions checks each version against `^\d+\.\d+\.\d+$`.
- **Parsing** a code requires exactly the six entries, in table order: `d(\d+\.\d+\.\d+)-s(\d+\.\d+\.\d+)-n(\d+\.\d+\.\d+)-p(\d+\.\d+\.\d+)-h(\d+\.\d+\.\d+)-b(\d+\.\d+\.\d+)`.
- Both raise an error naming the package and version that doesn't match.

</details>

# Proposed solution

## dandi-schema

Add a `ValidatorType` enum and two read-only fields to `Dandiset`: `validatedRequiredVersions` and `validatedBy`. Map-valued fields keyed by an enum already exist (`BareAsset.digest: Dict[DigestType, str]`).

<details>
<summary>Implementation</summary>

```python
class ValidatorType(Enum):
    """Packages whose versions identify a Dandiset validation record"""

    dandi = "dandi"
    dandischema = "dandischema"
    nwbinspector = "nwbinspector"
    pynwb = "pynwb"
    hdmf = "hdmf"
    bids_validator_deno = "bids-validator-deno"


class Dandiset(CommonModel):
    ...
    validatedRequiredVersions: Optional[Dict[ValidatorType, str]] = Field(
        None,
        title="Validator versions required for the validation record",
        description="Exact versions of the validators whose validation record determines "
        "whether this version is valid. Set by the archive.",
        json_schema_extra={"readOnly": True, "nskey": DANDI_NSKEY},
    )
    validatedBy: Optional[bool] = Field(
        None,
        description="Whether a validation record produced with exactly "
        "validatedRequiredVersions exists for this version's content and has no errors. "
        "None if no such record exists yet. Set by the archive.",
        json_schema_extra={"readOnly": True, "nskey": DANDI_NSKEY},
    )
```

</details>

`validatedBy` has three states:

| Value | Meaning |
|---|---|
| `null` | Not run: no complete record exists yet for the current content. This covers queued and running validation, and runs that could not complete. |
| `false` | Failed: the record has at least one `ERROR` or `CRITICAL` result. |
| `true` | Passed. |

Extend `Dandiset.check_publication_status` so that a published Dandiset with `validatedRequiredVersions` set must have `validatedBy: true`. The rule only applies when `validatedRequiredVersions` is set: already-published metadata, which lacks the field, stays valid, and archive instances that don't enable the feature are unaffected. The error names the value, as it appears in JSON, and the required versions, for example:

> `validatedBy` is `false`: content validation with `dandi==0.75.0`, `dandischema==0.12.0`, `nwbinspector==0.7.1`, `pynwb==3.1.0`, `hdmf==4.1.0`, `bids-validator-deno==2.1.0` found errors, and it must pass before publishing

<details>
<summary>Implementation</summary>

Inside the branch for published Dandisets (the one where `datePublished` is set):

```python
if self.validatedRequiredVersions is not None and self.validatedBy is not True:
    versions = ", ".join(
        f"`{package.value}=={version}`"
        for package, version in self.validatedRequiredVersions.items()
    )
    if self.validatedBy is False:
        value, problem = "false", f"content validation with {versions} found errors"
    else:
        value = "null"
        problem = f"content validation with {versions} has not finished for the current files"
    err(
        "validatedBy",
        f"`validatedBy` is `{value}`: {problem}, and it must pass before publishing",
    )
```

The message follows the shape of the existing ones (e.g. "publishedBy is required for a published Dandiset"), with field names, values and package versions in backticks so they render as code.

</details>

The new fields bump the schema version.

<details>
<summary>Implementation</summary>

- Bump `DANDI_SCHEMA_VERSION`, and add the previous version to `ALLOWED_INPUT_SCHEMAS` and `ALLOWED_TARGET_SCHEMAS`.
- Make `migrate()` drop both fields unconditionally when downgrading below the new version. `SIMPLE_DOWNGRADES` raises on non-empty values, and `validatedBy` is never empty once stamped; the archive re-stamps both fields anyway.

</details>

## dandi-archive

### Content fingerprint

The fingerprint is a dataset-level checksum of the version's `(path, digest)` pairs. `digest` is the blob's DANDI etag (`AssetBlob.etag`) or the Zarr checksum (`ZarrArchive.checksum`). Zarr assets are included because layout and BIDS checks still see their paths, even though their content is not checked. Dandiset-level metadata is excluded, because the archive already validates it independently.

- **Updated in O(1).** The fingerprint is a multiset hash, so each asset change updates it in constant time instead of rehashing every asset.
- **Pairing.** Each result is stored with the fingerprint and version code it was produced for.

<details>
<summary>Implementation</summary>

- **How.** Each `(path, digest)` pair is hashed to an element. The version stores the element-wise sum of its pairs' elements as its fingerprint state, and the fingerprint is the SHA-256 of that state.
- **Assets.** Adding an asset adds its element, removing one subtracts it, and replacing one does both. Every asset change goes through `_add_asset_to_version` and `_remove_asset_from_version` (`services/asset/`), which update the state in the same transaction after locking the Version row with `select_for_update()`, so parallel uploads can't lose an update. The etag is known at upload, so the later arrival of `sha256` does not change the fingerprint.
- **Zarr checksums.** A Zarr's checksum changes several times: `mark_pending()` sets it to `None` on every Zarr upload or delete ([`zarr/models.py`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/zarr/models.py#L111-L115), called from [`zarr/views/__init__.py`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/zarr/views/__init__.py#L331)), ingestion [sets it to `None`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/zarr/tasks/__init__.py#L44-L46) when it starts, and ingestion [sets the new value](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/zarr/tasks/__init__.py#L79) when it ends. Each of these replaces the element of every draft asset that points to the Zarr, in the same transaction. A Zarr without a checksum contributes the element of `(path, '')`.
- **Construction.** Use a multiset hash with a large state, such as LtHash (1024 16-bit lanes, 2 KB; Lewi et al., 2019). A plain sum of SHA-256 digests modulo 2^256 is cheaper, but generalized-birthday attacks make it practical to craft a set of files that collides with another.
- **Backfill.** Existing versions get a one-off O(n) computation. The same management command can recompute any version from scratch to check for drift.

</details>

### Required versions

Each draft stores its required version code in a new `Version` column, next to its content fingerprint.

- **Moved on file changes.** A file change is any change to the fingerprint's value: an asset added, removed, or replaced by different content or at a different path. The same update sets the required code to the current target. A draft therefore moves to newer validators only when its files change, and a new validator release re-validates nothing and doesn't interrupt publication.
- **Kept otherwise.** Metadata-only changes leave the fingerprint, and so the required code, unchanged. That includes edits to an asset's metadata alone: [`change_asset`](https://github.com/dandi/dandi-archive/blob/4f7637d7ef1f61a237a937c2f7f4eff6c4d16fd1/dandiapi/api/services/asset/__init__.py#L141-L148) removes and re-adds the asset, but with the same blob and path the fingerprint's value doesn't change. The draft keeps its result, needs no new run, and is never blocked by checks added later.
- **Published versions:** see [Publication](#publication).
- **Unset.** Drafts without a required code get the current target as soon as one exists.
- **Retired codes.** If a draft's required code is not the target and the draft has no complete row for it (for example, its run failed before a new image was released), the draft moves to the target, and the reconciler marks the draft's queued or running rows for the retired code `superseded`.

<details>
<summary>Implementation</summary>

New `Version` columns:

```python
class Version(PublishableMetadataMixin, TimeStampedModel):
    ...
    fingerprint_state = models.BinaryField(null=True)  # multiset hash state
    content_fingerprint = models.CharField(max_length=64, null=True)  # SHA-256 of the state
    required_validators = models.CharField(max_length=255, null=True)  # version code
```

</details>

### No caching across jobs

Per-asset results are not kept from one job to the next, because an asset's result can depend on other files. For example, if a video file's path changes without updating the `ImageSeries` that points to it, the NWB file itself becomes invalid even though its own content is unchanged. So every job validates the whole Dandiset.

### Settings

- **`DJANGO_DANDI_VALIDATION_GATING`** (boolean, off by default). When on, both fields are stamped into draft metadata and publication is gated. When off, both fields are removed from each draft the next time it goes `PENDING`, so turning gating off takes effect gradually.

The validation target is not a setting (see [Version updates](#version-updates)), and the worker's token is described under [Job API](#job-api).

### Summary table

Each validation attempt is a row in a new `VersionValidationSummary` table, which also serves as the job queue: the worker app uses no Celery broker.

- **One row per attempt.** Rows are keyed by version, version code and fingerprint. A rerun of the same key (after a failure, a stopped heartbeat, or `--force`) adds a row instead of overwriting one, and at most one row per key is queued or running at a time. The current result for a key is its newest `complete` row. Only the current result for the Version's required code and fingerprint affects publication; rows for other codes are informational.
- **Provenance.** Each row's summary records the archive release (`importlib.metadata.version('dandiapi')`) and the digest of the worker image that ran it.
- **History.** Rows and their records are never deleted, so every past result, including failed and superseded ones, stays available. Rows also outlive their Version: deleting a Dandiset sets the foreign key to null, and the row keeps the Dandiset identifier and version string.
- **Admin.** The table is registered in Django admin, so staff can review rows.

**Job states.** Each row moves through these states:

| State | Entered when | Left when |
|---|---|---|
| `queued` | The manifest hook or the reconciler queues the draft (see [Triggering](#triggering)). | A worker claims it (→ `running`), or the draft's fingerprint or required code changes first (→ `superseded`). |
| `running` | A worker claims it. The worker sends heartbeats with its progress (files done of total). | The worker reports a summary (→ `complete`, or `superseded` if the draft changed during the run), or reports a failure, stops sending heartbeats, or passes the job's time limit (→ `failed`). |
| `complete` | The worker reported a summary and the draft still has the job's fingerprint. | `revalidate_content --force` (→ `superseded`). |
| `failed` | See `running`. `success` stays empty and Sentry is notified. | Never. The reconciler queues a new row for the key, up to a fixed number of attempts (see the "Retry thresholds" [open question](trusted-validation.md#open-questions)). After that, only `--force`, a file change, or a new target starts another, and the banner says "Could not complete — staff notified". |
| `superseded` | The draft's content or required code changed before the result could be used, or `--force`. | Never. |

<details>
<summary>Implementation</summary>

```python
class VersionValidationSummary(TimeStampedModel):
    version = models.ForeignKey(
        Version, related_name='validation_summaries', null=True, on_delete=models.SET_NULL
    )
    dandiset_identifier = models.CharField(max_length=16)  # kept if the Version is deleted
    version_string = models.CharField(max_length=16)
    validators = models.CharField(max_length=255)  # version code
    content_fingerprint = models.CharField(max_length=64)
    state = models.CharField(max_length=10)  # queued, running, complete, failed, superseded
    success = models.BooleanField(null=True)  # set only for complete runs
    files_done = models.PositiveIntegerField(default=0)  # progress, from heartbeats
    files_total = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict)  # counts, top issues, checked/not-checked counts, record path, resource usage, archive release, image digest
    requested_at = models.DateTimeField(auto_now_add=True)
    heartbeat_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['version', 'validators', 'content_fingerprint'],
                condition=models.Q(state__in=['queued', 'running']),
                name='unique-live-validation-run',
            )
        ]
```

A key's attempts are its rows, so there is no attempts counter.

</details>

### Triggering

Validation jobs are `queued` rows of the summary table. The archive queues them in two ways, both only once a target exists (see [Version updates](#version-updates)):

- **Manifest hook:** at the end of `write_manifest_files`, for drafts only.
- **Reconciler:** a beat task every few minutes. It is what guarantees coverage, because checksums arrive after the manifests are written and the draft is not re-pended then. The hook only cuts latency. The reconciler also queues retries of failed runs (see [Summary table](#summary-table)).

A draft is eligible when all of these hold. Queuing is idempotent, and the claim checks them again:

- every blob asset has a `sha256` and every Zarr is `COMPLETE`;
- it has no complete row for its required code and current fingerprint, and no queued or running row for them.

Published versions are never queued (see [Publication](#publication)), and versions published before this feature have no result.

<details>
<summary>Implementation</summary>

Publishing and some management commands also call `write_manifest_files` for published versions, so the hook checks `version.version == 'draft'`.

</details>

### Job API

A small API lets the worker app claim jobs and report results. It authenticates with `DJANGO_DANDI_VALIDATION_WORKER_TOKEN`, a secret bearer token checked by its own permission class rather than a user account, and these endpoints are all the token opens.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/validation/jobs/claim/` | Claim the oldest queued job for the worker's version code; returns the job, or nothing |
| `POST` | `/api/validation/jobs/{id}/heartbeat/` | Keep a running job alive and report its progress |
| `POST` | `/api/validation/jobs/{id}/complete/` | Report the summary after uploading the record |
| `POST` | `/api/validation/jobs/{id}/fail/` | Report a run that could not complete |

### Validation job

The work is split between the archive and the worker app.

1. **Claim (archive).** The worker calls the claim endpoint with its version code. The archive marks the oldest queued job for that code as running, and returns the draft's stored fingerprint, its assets with download URLs, and presigned upload URLs for the results. A queued job whose draft no longer has the job's fingerprint is marked `superseded`, and the next job is returned instead.

   <details>
   <summary>Implementation</summary>

   The claim runs in one transaction with `select_for_update(skip_locked=True)`. The job contains:
   - the draft's stored fingerprint;
   - each asset's path, size and `sha256`, with a direct S3 URL, never the API download URL. URLs for embargoed blobs are presigned, with an expiry at least as long as the job's time limit;
   - the `identifier`, `name` and `description` for a minimal `dandiset.yaml`;
   - presigned upload URLs for the record and its provenance file (see [Record storage](#record-storage)).

   </details>
2. **Build the DataLad dataset (worker)** in a temporary directory from the job, without downloading the files' contents.

   <details>
   <summary>Implementation</summary>

   - annex keys `SHA256E-s{size}--{sha256}{ext}` registered with `git annex fromkey` and `registerurl --batch`;
   - small text files (`dataset_description.json`, sidecar `.json`/`.tsv`, `README`, `.bidsignore`) downloaded and committed to git;
   - Zarr paths present, since an empty directory would be skipped;
   - a minimal `dandiset.yaml` with non-empty `identifier`, `name` and `description` and no `schemaVersion`;
   - no FUSE mount.

   </details>
3. **Validate (worker).** Run `dandi validate --missing-file-content=stream --min-severity INFO -f json_lines` through `datalad containers-run`, wrapped in `duct`, so the run is recorded in the dataset and its resource use is measured.

   <details>
   <summary>Implementation</summary>

   - **`datalad containers-run`** records the run in the dataset: the command, the container and the outputs. It runs with `--explicit` and no `--input`, so nothing is fetched up front and files are streamed.
   - **In place.** The worker already runs inside the validator image, whether on a Heroku dyno or under Apptainer elsewhere (see [Validation worker app](#validation-worker-app)). So the dataset registers the image with a call format of `{cmd}` and a small image file holding the image's GHCR reference and digest, and the command runs in place.
   - **`duct`** (con-duct) captures stdout, stderr and resource usage: peak memory, CPU and wall time (`info.json`, `usage.jsonl`).

   </details>
4. **Process the results (worker).** Infrastructure failures are retried and, if they persist, the job is reported as failed rather than counted as content errors. A run is complete when every NWB and BIDS file has an outcome. Zarr-backed assets (NWB or BIDS stored as Zarr) are counted as "not checked" for now (see [Open questions](trusted-validation.md#open-questions)). In stream mode, dandi-cli also skips the checks that need a BIDS file's content, such as reading NIfTI headers, so those checks don't run.

   <details>
   <summary>Implementation</summary>

   This is the single list of workarounds for dandi-cli's current records (see [dandi-cli](#dandi-cli)):
   - make `path` relative to the Dandiset, and drop `dandiset_path` and `dataset_path`, which hold absolute temporary paths (NWB Inspector also sets them to the file's parent and grandparent directories instead of the Dandiset root);
   - strip URLs (presigned URLs carry credentials), drop `DANDI.FILE_CONTENT_STREAMED`, and group pynwb results under a fixed ID, since their IDs embed the error message;
   - exclude results for `dandiset.yaml`, since the archive validates metadata itself;
   - drop results for Zarr paths and paths inside them, which count as not checked (the Zarr placeholders would raise `zarr.missing_zarr_json`);
   - retry, with backoff, files whose results are streamed-read failures (their own ID; see [dandi-cli](#dandi-cli)) or `DANDI.FILE_CONTENT_MISSING`. Other `INTERNAL`-origin results, such as `pynwb.GENERIC` when pynwb can't read a corrupt file, count by their severity like any other result. If the retries keep failing, report the job as failed.

   </details>
5. **Report (worker).** Upload the JSONL record and the provenance file to the presigned URLs, then call the complete endpoint with the summary. Afterwards, delete the temporary dataset and dandi-cli's cache.

   <details>
   <summary>Implementation</summary>

   - The summary holds the counts by severity, the top issues, the checked and not-checked counts, duct's peak memory and wall time, and the image digest.
   - Throughout the run, the worker sends heartbeats with its progress (files done of total), which the archive stores on the row.

   </details>
6. **Store (archive).** Only `ERROR` and `CRITICAL` results block publication: for a complete run, `success` is true when there are none. The archive applies this policy, not the worker. If the draft's fingerprint changed during the run, the row is marked `superseded` and the reconciler queues a new run; otherwise the row is marked `complete` and the draft is stamped (see [Stamping](#stamping)). The draft is never set back to `PENDING`.

   <details>
   <summary>Implementation</summary>

   `success` is `counts.CRITICAL + counts.ERROR == 0`. dandi-cli maps validator severities onto its own as follows:
   - NWB Inspector: `CRITICAL`, `PYNWB_VALIDATION` and `ERROR` → `ERROR`, best-practice violations → `WARNING`. Best-practice suggestions are never reported, because dandi-cli runs NWB Inspector with `importance_threshold=BEST_PRACTICE_VIOLATION`.
   - BIDS validator: errors → `ERROR`, warnings → `HINT`.

   The fingerprint comparison runs under `select_for_update` on the Version row.

   </details>

### Validation worker app

- **Isolation.** The worker app holds no database, bucket or Django credentials: its config vars are only the archive's API URL, the worker token and a Sentry DSN. It reads files through URLs the archive hands out and writes records through presigned upload URLs (see [Record storage](#record-storage)). A crafted file that exploits a parser bug can therefore reach at most the worker token, which only opens the [job API](#job-api).
- **Process.** One process per dyno loops: claim a job, run it, report it, repeat, sleeping briefly when nothing is queued. Capacity scales with the number of dynos.
- **Restarts.** Heroku restarts dynos at least daily and on every release. An interrupted job stops sending heartbeats and fails (see the job states under [Summary table](#summary-table)).
- **Time limit.** Each job has a time limit, after which it fails. The limit can't exceed 7 days, the longest a presigned URL for an embargoed file can last. How it relates to Heroku's daily restart is the "Large Dandisets" [open question](trusted-validation.md#open-questions).
- **Elsewhere.** The same image runs outside Heroku, e.g. `apptainer run docker://ghcr.io/dandi/dandi-validation:<version code>` on HPC, either against the same job API or from a job file built from the public API. A job file reports to no archive and sets no target, which is how the pilot measures cost (see [Rollout details](#rollout-details)).

<details>
<summary>Implementation</summary>

- **Code check.** At startup the worker derives its version code from the installed packages (`importlib.metadata`) and refuses to run if it differs from the code the image was built for.
- **Subprocess.** The worker runs validation as a subprocess, so `dandi validate -J` works and a crash or out-of-memory kill only ends that run. The subprocess doesn't receive the worker token.

</details>

### Validator image

The validator image holds the six validator packages and the tools the worker needs, built from a pixi lock that the daily scan resolves (see [Version updates](#version-updates)).

- **What's pinned.** The lock pins, with checksums:
  - the six validator packages from PyPI, with dandi's `datalad` extra (datalad-fuse with the remfile backend), which streaming requires;
  - Python, git and git-annex from conda-forge;
  - DataLad, datalad-container and con-duct (`duct`), which the worker uses to build the dataset and run validation (see [Validation job](#validation-job)).

  git and git-annex therefore come from the lock, at exact versions, rather than from the base image's operating-system packages, which can change whenever the base image is rebuilt.
- **Lock kept with the image.** Each image carries its resolved `pixi.lock`, which is also attached to its GHCR entry, so the image itself records its environment.
- **Names.** GitHub Container Registry holds the canonical copy as `ghcr.io/dandi/dandi-validation:<version code>`, and the newest image is also tagged `latest`. The worker app's Heroku registry doesn't keep version tags, so GHCR records which image produced each code.

<details>
<summary>Implementation</summary>

One shared `validators/Dockerfile` builds from the resolved `pixi.toml` and `pixi.lock` and has two stages:
- **Build:** the official pixi image on Ubuntu (`ghcr.io/prefix-dev/pixi:<pixi version>-noble`) runs `pixi install --locked`.
- **Runtime:** plain `ubuntu:24.04` receives only the installed environment, its `pixi.lock`, an activation script from `pixi shell-hook`, and the worker's small program (see [Validation worker app](#validation-worker-app)), which doesn't import Django. pixi itself isn't needed at runtime.

Since the environment carries its own tools and libraries, the base image only has to provide the basics, such as glibc. Both base images are pinned by digest.

</details>

### Version updates

New validator versions are picked up automatically. Neither the validator versions nor the images are committed to any repository: dandi-archive holds only an unpinned [pixi](https://pixi.sh) manifest (`validators/pixi.toml`) listing the packages, and the Dockerfile.

1. **Daily scan.** A scheduled GitHub Actions workflow in dandi-archive runs once a day. It resolves the manifest with `pixi lock`, which picks the newest releases of the six validator packages that install together, and reads their versions from the lock.
2. **Version check.** Each version must be a plain release (see [Validator versions](#validator-versions)). If any isn't, the workflow fails with an error naming the package and version, and alerts.
3. **Only new versions.** The workflow computes the version code. If GHCR already has an image tagged with it and that image is released to the worker apps, nothing has changed and the workflow stops. If only the release is missing, for example because an earlier run failed after pushing, it releases the existing image.
4. **Build and test.** Otherwise it builds the image from the lock and runs a smoke test on a small fixture Dandiset.
5. **Push and release.** It pushes the image to GHCR tagged with the code and `latest`, then to the worker apps' Heroku registries, and releases it there.
6. **Target.** Workers report their image's version code with every claim, and the validation target is the most recently first-seen version code reported by a worker. "Newest" therefore means first seen, not highest version. Until a worker has reported a code, the feature is off: nothing is queued or stamped. The archive accepts only codes that parse and whose image exists in GHCR. Staff can override the target in Django admin (e.g. after rolling back an image), and it is exposed as `validation_target` on `/api/info/`.

<details>
<summary>Implementation</summary>

- **Immutable images.** An image is built only for a code GHCR doesn't have yet, and is never rebuilt, so one code always names one image. The other tools in the lock (git, git-annex, DataLad, datalad-container, con-duct) are re-resolved only when a new code is built. A fix to the worker program therefore ships with the next validator release.
- **Incompatible releases.** If the newest releases can't be installed together, the resolver falls back to the newest set that can, so the scan never builds a broken environment.

</details>

### Record storage

Each row's full JSONL record goes in the archive bucket at:

```
dandisets/{id}/validation/{code}/{fingerprint}/{row id}.jsonl
dandisets/{id}/validation/{code}/{fingerprint}/{row id}.provenance.json
```

The provenance file holds the `datalad containers-run` record, duct's `info.json` and the image digest.

- **Written once.** Each row's record is written once, so it never needs pinning to an object version.
- **Shared.** The published Version's copied row points to the draft row's record, so the two share the same object.
- **Upload and embargo.** The worker uploads each record through the presigned URLs in its job. The archive signs those URLs with the `embargoed` tag when needed, because the bucket is otherwise publicly readable, and removes the tag at unembargo. If the Dandiset is unembargoed while a run is in progress, the complete endpoint removes the tag from the new record.

<details>
<summary>Implementation</summary>

- Pinning to an object version wouldn't work anyway, since the lifecycle rule deletes older noncurrent versions under `dandisets/`.
- At unembargo, tags are removed by listing the `dandisets/{id}/validation/` prefix, since the existing helper only covers the five fixed manifest paths.

</details>

### Stamping

A shared helper, `stamp_validation_fields(version)`, is called by `validate_version_metadata`, when a job is stored, and when staff override a result. The last two stamp only a `VALID` or `INVALID` draft: a `PENDING` or `VALIDATING` draft is stamped by the normal path, and a `PUBLISHING` or `PUBLISHED` draft is never touched.

- **No timestamp change.** Stamping doesn't bump `Version.modified` when only these two fields change, so the "Last update" date only moves for real content changes.
- **Gating.** Draft validation is publish-time validation (see [Current state](#current-state)). So whenever `validatedBy` is not `true`, the new schema rule produces an ordinary validation error on `validatedBy`, and the draft becomes `INVALID`. The existing publish gating handles the rest, and **the publish service needs no new check**.
- **Owners can't set them.** `Version.strip_metadata` adds both fields to its computed fields, so owners cannot set them through the metadata editor or the API.

<details>
<summary>Implementation</summary>

```python
def _validation_fields(version: Version) -> dict | None:
    if not settings.DANDI_VALIDATION_GATING or version.required_validators is None:
        return None  # remove both fields
    row = (
        version.validation_summaries.filter(
            validators=version.required_validators,
            content_fingerprint=version.content_fingerprint,
            state='complete',
        )
        .order_by('-created')
        .first()
    )
    passed = row.success if row else None  # None: no complete record for this content yet
    return {
        'validatedRequiredVersions': parse_version_code(version.required_validators),
        'validatedBy': passed,
    }
```

- **Writes.** The helper merges the fields into the draft's metadata, re-runs schema validation, and writes `status`, `validation_errors` and `metadata` with `.update()`. Today `validate_version_metadata` always sets `modified=now`; it skips that when the only metadata change is to these two fields, since content changes already bump `modified` themselves (see also [#2950](https://github.com/dandi/dandi-archive/pull/2950)).
- **Concurrency.** The concurrent `aggregate_assets_summary` task already uses optimistic concurrency on `metadata`, so it retries if stamping changed the metadata underneath it.

</details>

### Publication

Published versions are frozen. The published Version inherits both fields from the draft's metadata, and the draft's fingerprint and required code, and never changes them. Published metadata is immutable, so the published Version stays tied to those validator versions permanently, and since publication requires `validatedBy: true`, its result is always a passing one.

Publishing also copies the draft's current result for its required code to the new published Version, as a row pointing at the same record (see [Record storage](#record-storage)). The published Version's banner shows the result straight away, and its content is never validated twice.

<details>
<summary>Implementation</summary>

`_publish_dandiset`'s final `validate(..., 'PublishedDandiset')` enforces the rule a second time.

</details>

### Read API

There are no separate validation endpoints. `/api/dandisets/{id}/versions/{version}/info/`, which the landing page already loads, applies the existing embargo check and gains:

- **`validation_summary`:** the current result for the Version's required code and current fingerprint. If there is none, the newest complete row for this version, with `stale` set. `null` if there is no complete row at all.
- **`stale`:** true when `validation_summary` was produced for content or validators the version no longer has.
- **`validation_run`:** the state of the current run, if any: queued, running (with files done of total), or failed.

Both metadata fields also appear in the raw metadata at `GET /api/dandisets/{id}/versions/{version}/`.

<details>
<summary>Implementation</summary>

The three fields are added to `VersionDetailSerializer`.

</details>

### Frontend

- **Banner** at the top of the landing page, driven by `/versions/{version}/info/`:
  - "Content validation queued", "Running (n of m files)", or "Could not complete — staff notified";
  - error styling if errors were found, warning styling if only warnings were found, and a small "validated" chip if it passed;
  - text naming the validators and their versions;
  - "results predate the latest changes" when `stale`;
  - "Zarr assets not checked" when applicable.
- **Pending, not error.** While `validatedBy` is `null`, its validation error is shown as pending, not counted in the error total, and the Publish button says "Waiting for content validation". The page polls `/info/` while a run is queued or running.
- **Details:** the validation dialog gains a tab built from `top_issues`, plus a link to the full record. Each issue maps to the dialog's existing `{field, message, path}` shape, so grouping by path works unchanged.
- **Validation error:** a clearer message and icon for the `validatedBy` error.

<details>
<summary>Implementation</summary>

- **Banner:** `DandisetMain.vue`.
- **Pending:** `DandisetPublish.vue` (`publishDisabledMessage`, `publishButtonDisabled`) disables publishing on any version validation error, and `DandisetValidationErrors.vue` counts every one as a "metadata validation error". Both treat the `null` `validatedBy` error as pending instead.
- **Details:** a new tab in `ValidationErrorDialog.vue`.
- **Validation error:** an entry for `validatedBy` in `VALIDATION_ICONS`.

</details>

### Search

Free-text search leaves out the two fields, so searches for "pynwb" or "hdmf" don't match every stamped version.

<details>
<summary>Implementation</summary>

Free-text search casts the whole metadata to text (`Cast('metadata', TextField())` in `views/dandiset.py`). Remove the two fields with the jsonb `-` operator before the cast.

</details>

### Management commands

A `revalidate_content` command does two things:

- **`--force`** marks a version code's complete rows on drafts `superseded`, so the reconciler re-runs them. It is meant for problems outside the image, such as a fix to the archive's store step or a storage outage that spoiled results. A fix to the worker program ships with the next validator release (see [Version updates](#version-updates)). Published versions' rows are never touched.
- **Override** sets a row's `success`, writes an admin audit record, and re-stamps the draft (see [Stamping](#stamping)).

### Monitoring

The archive monitors how long drafts wait for a result, so a stalled worker is noticed (see [Publication latency](trusted-validation.md#publication-latency-accepted-trade-off)).

- **Daily check.** A daily task emails `DANDI_DEV_EMAIL` with each draft that has waited more than three days for a result, and how long it has waited. Embargoed drafts are listed in a separate section, since they don't block owners yet.

  <details>
  <summary>Implementation</summary>

  The task is a beat task scheduled like `send_pending_users_email`. It looks only at each draft's newest row for its required code and current fingerprint, and selects:
  - drafts whose newest row has been queued or running for more than three days since its first attempt's `requested_at`, or has failed with no retries left;
  - as a fallback, drafts that were never queued: no row for their required code and current fingerprint, and `modified` older than three days.

  </details>
- **Alerts.** Sentry reports errors from both apps, and an alert fires when the number of queued jobs grows past a threshold.

## dandi-infrastructure

- **Worker app.** A new Heroku app (and a staging counterpart) on the container stack, sized from the pilot. Its config vars are listed under [Validation worker app](#validation-worker-app).
- **Archive config vars.** `DJANGO_DANDI_VALIDATION_GATING` (off until the last rollout step), and the worker token as a secret.
- **Releases.** A Heroku API key, stored as a GitHub Actions secret in dandi-archive, lets the daily scan release images to the worker apps (see [Version updates](#version-updates)).
- **No storage changes.** Records go in the existing bucket (see [Record storage](#record-storage)).

<details>
<summary>Implementation</summary>

- **Worker app:** a `heroku_app` resource with `stack = "container"`. Its `heroku_formation` for the `worker` process can only be created once a release defines that process type, so it is added after the daily scan's first release, at quantity 0 (`standard-2x` has only 1 GB of memory).
- **Archive config vars:** add the gating variable under `# DANDI-specific variables` in `terraform/api.tf`, and in `staging.tf` if staging should validate too. Add `DJANGO_DANDI_VALIDATION_WORKER_TOKEN` to `sensitive_config_vars`, from the same Terraform variable as the worker app's token:

```hcl
DJANGO_DANDI_VALIDATION_GATING = "false"  # "true" at the last rollout step
```

</details>

## dandi-cli

- **Release the streaming stack** ([#1955](https://github.com/dandi/dandi-cli/pull/1955), [#1956](https://github.com/dandi/dandi-cli/pull/1956)). It currently depends on datalad-fuse by git URL, which PyPI rejects, so it needs a datalad-fuse release with the remfile backend first.
- **Give streamed-read failures their own ID**, e.g. `DANDI.FILE_CONTENT_STREAM_FAILED`. Today they would share `INTERNAL` origin with results caused by bad content, such as `pynwb.GENERIC` when pynwb can't read a corrupt file, so the worker couldn't tell a read worth retrying from an error to report.
- **Record hdmf's version.** pynwb validation runs on hdmf, but records only carry pynwb's version, because dandi-cli has no `hdmf` validator. Add an optional `Origin` field for the versions of libraries a validator depends on (bumping `record_version`), and fill it with hdmf's version in pynwb and NWB Inspector records.
- **Release the NWB Inspector version fix.** Every NWB Inspector record from dandi-cli 0.81.0 reports `validator_version: ""`. [#1966](https://github.com/dandi/dandi-cli/pull/1966) fixes this on master, and needs a release. The worker reads versions from its image, so this is a consistency fix rather than a prerequisite.
- **Paths, IDs and `dandiset_path`.** Records contain absolute local paths, pynwb result IDs embed the error message (`pynwb.<message>`), and NWB Inspector results set `dandiset_path` and `dataset_path` to the file's parent directories instead of the Dandiset root. Each can be fixed in dandi-cli later; meanwhile the worker works around them (see [Validation job](#validation-job), step 4).

# Lifecycles

How a draft's `Version.status` changes. These assume gating is on.

**Draft with changed files.**

1. The owner changes the draft's files. Its fingerprint and required versions update (see [Required versions](#required-versions)), and the draft goes `PENDING`.
2. Stamping sets `validatedBy` to `null`. The draft becomes `INVALID` with the rule's "has not finished" error (see [dandi-schema](#dandi-schema)), which the UI shows as pending.
3. A job is queued and run (see [Triggering](#triggering) and [Validation job](#validation-job)).
4. When the result is stored, `true` makes the draft `VALID` and publishable, and `false` keeps it `INVALID` with the issues listed. A superseded run leaves the draft at step 2.

**Metadata-only edit.**

1. The owner edits only the draft's metadata, and it goes `PENDING`.
2. The draft keeps its required versions and result (see [Required versions](#required-versions)). No run is queued.
3. If that result passed, the draft becomes `VALID` straight away and can be published, even if the target has moved on since.

# Rollout details

The specifics of each step of the [Proposed Rollout Order](trusted-validation.md#proposed-rollout-order), with the same numbering.

1. **dandi-schema:** release with the changes under [dandi-schema](#dandi-schema), including the schema version bump.
2. **datalad-fuse:** release with the remfile backend, so the dandi-cli release can depend on it (see [dandi-cli](#dandi-cli)).
3. **dandi-cli:** release with the changes under [dandi-cli](#dandi-cli).
4. **dandi-infrastructure:** create the worker apps (staging and production), and set the token on both the archive and worker apps, with gating `"false"`. The worker formation comes after step 5's first release (see [dandi-infrastructure](#dandi-infrastructure)).
5. **dandi-archive:** upgrade dandischema and run `migrate_version_metadata --all` first, then ship everything under [dandi-archive](#dandi-archive) with gating off, including the worker's ability to run a job from a file (used by the pilot). The fingerprint backfill runs here; report how long it took. The daily scan then releases the first image to the worker apps, which run no dynos yet, so no target is set.
6. **Pilot:**
   - On staging, scale the worker up and test the whole flow: job API, worker start time, stamping and the banner.
   - For cost, run the released image outside the archive, from job files for a small, a BIDS and a large production Dandiset (see [Validation worker app](#validation-worker-app)). Use duct's summaries to measure seconds per file, peak memory, bytes read, how long re-validating the largest Dandiset takes after a one-file change, and how that compares with Heroku's daily dyno restart. Then choose the dyno size and count.
7. **Shadow mode:** scale the production worker up. Its first claim sets the target, existing drafts get it as their required versions (see [Required versions](#required-versions)), and every draft is queued, which starts step 8.
8. **Sweep:** only drafts are swept (see [Publication](#publication)).
   - **Capacity:** `files × seconds per file ÷ processes`. For example, 500k files at 30 seconds each is about 170 process-days, or about 11 days with 16 processes.
   - **Regions:** Heroku's US region runs in AWS us-east-1, while the bucket is in us-east-2.
9. **Review:** from the summary table and the full records, count how many drafts gating would block and by which checks, and look for false positives. Summarize run time and memory from duct's summaries. Archive-side fixes are re-run with `revalidate_content --force`; worker fixes ship with the next validator release (see [Management commands](#management-commands)).
10. **Turn gating on:** tell the owners whose drafts the review found would be blocked, set `DJANGO_DANDI_VALIDATION_GATING` to `"true"`, then set drafts to `PENDING` so they are stamped. The existing `revalidate --versions` management command cannot do this as is: `validate_version_metadata` returns early unless a version is `PENDING`, so the command must first set them `PENDING`.
