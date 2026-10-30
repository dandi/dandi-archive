# Trusted File and Dataset Validation

Authors: Cody Baker

Status: proposal

# Contents

- [Overview](#overview)
  - [Goals](#goals)
  - [Summary](#summary)
- [Terminology](#terminology)
- [Current state](#current-state)
- [Proposed solution](#proposed-solution)
  - [dandi-schema](#dandi-schema)
  - [dandi-archive](#dandi-archive)
    - [Settings](#settings)
    - [Validator image](#validator-image)
    - [Version updates](#version-updates)
    - [Triggering](#triggering)
    - [Content fingerprint](#content-fingerprint)
    - [Required versions](#required-versions)
    - [No caching across jobs](#no-caching-across-jobs)
    - [Validation job](#validation-job)
    - [Summary table](#summary-table)
    - [Record storage](#record-storage)
    - [Stamping](#stamping)
    - [Publication](#publication)
    - [Read API](#read-api)
    - [Management commands](#management-commands)
    - [Search](#search)
    - [Job API](#job-api)
    - [Validation worker app](#validation-worker-app)
    - [Frontend](#frontend)
  - [dandi-infrastructure](#dandi-infrastructure)
  - [dandi-cli](#dandi-cli)
  - [Publication latency (accepted trade-off)](#publication-latency-accepted-trade-off)
  - [Old files vs. new checks (accepted trade-off)](#old-files-vs-new-checks-accepted-trade-off)
- [Lifecycles](#lifecycles)
- [Rollout](#rollout)
- [Alternatives to consider](#alternatives-to-consider)
- [Open questions](#open-questions)

# Overview

## Goals

- A Dandiset version cannot be published unless a trusted validation record for its current content contains no errors.
- The record must come from an exact, known set of validator versions:
  - **Drafts:** the latest set the archive was configured for at the draft's last file change (an asset added, removed or replaced). Metadata-only changes don't move it.
  - **Published versions:** the set frozen at publication, which is only possible if the version was valid then, so later validator releases never make them invalid.
- Errors and warnings are shown to everyone in a banner on the Dandiset landing page ([#1486](https://github.com/dandi/dandi-archive/issues/1486)). Warnings do not block publication but reflect overall quality.
- Changes only to the metadata of previously published versions should not trigger version bumps for dataset validation.

## Summary

Today the archive only validates simple asset-level metadata: each Asset's metadata is compared against the `PublishedAsset` schema, and the draft Version's metadata against the `PublishedDandiset` schema.

Neither the archive backend nor any external service runs the validators that check the *contents* of files nor the *layout* of datasets: NWB Inspector, PyNWB validation, BIDS validator, or even the ad-hoc DANDI layout enforced by CLI command `dandi validate`. As a result, Dandisets with invalid NWB files or BIDS/DANDI layouts can be published (e.g. [#2412](https://github.com/dandi/dandi-archive/issues/2412)).

This document proposes running `dandi validate` over every draft Dandiset in a dedicated validation worker: a separate Heroku app that runs a container image. After a draft's asset manifests are written, the archive queues a job, and the worker claims it, builds a DataLad dataset from the version's assets and streams validation through dandi-cli's datalad-fuse support ([dandi/dandi-cli#1955](https://github.com/dandi/dandi-cli/pull/1955), [#1956](https://github.com/dandi/dandi-cli/pull/1956), [#1957](https://github.com/dandi/dandi-cli/pull/1957)). This approach simplifies the majority of modifications that would be required to both the BIDS-Validator and the NWB Inspector to adapt them away from filesystems (even symlinked 'mock' ones as DataLad creates).

- **Results:** each draft Dandisets metadata gets two new fields: the exact validator versions its result must come from (corresponding generally to the 'latest' at time of last asset modification), and whether that result passed or failed (with detailed JSON record of all errors, warnings, etc.). A summary of each result goes in a new table, and the full record goes in the archive bucket.
- **Gating:** the archive blocks publication unless that result has no errors.

The changes in each repository can be summarized as:

| Repository | Change |
|---|---|
| dandi-schema | A `ValidatorType` enum, two read-only `Dandiset` fields, one publication rule, one schema version bump |
| dandi-archive | One table, a small job API for the worker, a scheduler, the worker's container image, a few lines in draft validation and publishing, `/info/` fields, a banner, a daily check |
| dandi-infrastructure | A new Heroku container app for the worker, and config vars on both apps |
| dandi-cli | A release with the streaming stack and small fixes |
| datalad-fuse | A release with the remfile backend, so dandi-cli can depend on it |

# Terminology

- **Validator versions:** the map from each package that affects validation results to the exact version used to produce a record. Keys are plain distribution names, and all six are always present:

  ```json
  {"dandi": "0.75.0", "dandischema": "0.12.0", "nwbinspector": "0.7.1", "pynwb": "3.1.0", "hdmf": "4.1.0", "bids-validator-deno": "2.1.0"}
  ```

  - **Source:** all six are read from the validator image that produced the record (see [Validator image](#validator-image)). `dandischema` here is that image's dandischema, not the archive's own dandischema library or the metadata's `schemaVersion`.
  - **Sanity check:** every key also appears in the records. Five appear as a record's `origin.validator` with its `origin.validator_version`, and `hdmf` appears alongside `pynwb`, since pynwb validation runs on hdmf (see [dandi-cli](#dandi-cli)).
- **Version code:** a short, readable string form of a validator-versions map. It names the validator environment's directory and container image tag, the archive's setting, and the record's path in the bucket.
  - **Form:** each package's one-letter code (see `VALIDATOR_CODES` under [Validator image](#validator-image)) followed directly by its version, in the code table's order, with entries joined by `-`. For the map above: `d0.75.0-s0.12.0-n0.7.1-p3.1.0-h4.1.0-b2.1.0`.
  - **Why this is unambiguous:** codes are single letters, and versions must be plain releases made only of digits and periods (e.g. `0.75.0`), so `-` never appears inside an entry. A pre-release, post-release, dev or local version (e.g. `1.0rc1`, `0.75.0+12.gabc`) cannot be encoded. The fixed order means equal maps always give identical codes.

  <details>
  <summary>Implementation</summary>

  - **Parsing:** split on `-`; each entry matches `([a-z])(\d+(?:\.\d+)*)`, and a whole code matches `[a-z]\d+(?:\.\d+)*(?:-[a-z]\d+(?:\.\d+)*)*`.

  </details>

- **Validation target:** the version code of the newest released worker image, which tracks the latest validator releases on PyPI (see [Version updates](#version-updates)).
- **Required versions:** the version code a draft must be validated with: the validation target at the draft's last file change (see [Required versions](#required-versions)).
- **Content fingerprint:** a hash of the files a version contains (see [Content fingerprint](#content-fingerprint)).

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

Extend `Dandiset.check_publication_status` so that a published Dandiset with `validatedRequiredVersions` set must have `validatedBy: true`. The rule only applies when `validatedRequiredVersions` is set: already-published metadata, which lacks the field, stays valid, and archive instances that don't enable the feature are unaffected. The error names the value and the required versions, for example:

> `validatedBy` is `False`: content validation with `dandi==0.75.0`, `dandischema==0.12.0`, `nwbinspector==0.7.1`, `pynwb==3.1.0`, `hdmf==4.1.0`, `bids-validator-deno==2.1.0` found errors, and it must pass before publishing

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
        problem = f"content validation with {versions} found errors"
    else:
        problem = f"content validation with {versions} has not finished for the current files"
    err(
        "validatedBy",
        f"`validatedBy` is `{self.validatedBy}`: {problem}, and it must pass before publishing",
    )
```

The message follows the shape of the existing ones (e.g. "publishedBy is required for a published Dandiset"), with field names, values and package versions in backticks so they render as code.

The schema change also needs some housekeeping:
- bump `DANDI_SCHEMA_VERSION`, and add the previous version to `ALLOWED_INPUT_SCHEMAS` and `ALLOWED_TARGET_SCHEMAS`;
- make `migrate()` drop both fields unconditionally when downgrading below the new version. `SIMPLE_DOWNGRADES` raises on non-empty values, and `validatedBy` is never empty once stamped; the archive re-stamps both fields anyway.

</details>

## dandi-archive

### Settings

- **No hardcoded target.** The validation target is not a config var. The archive records the version code each worker reports when it claims jobs, and the target is the most recently first-seen code, i.e. the newest released worker image (see [Version updates](#version-updates)). Until a worker has reported a code, the feature is off: nothing is validated or stamped. The target is shown in Django admin, where staff can override it (e.g. after rolling back an image), and exposed as `validation_target` on `/api/info/`.
- **`DJANGO_DANDI_VALIDATION_GATING`** (boolean, off by default). When on, both fields are stamped into draft metadata and publication is gated. When off, stamping removes them.
- **`DJANGO_DANDI_VALIDATION_WORKER_TOKEN`** (secret) authenticates the worker app to the [job API](#job-api).

With a worker running and gating off, the archive runs in shadow mode: results and the banner appear, but publication is not gated.

### Validator image

- **One environment per version code.** Each version code has a directory in dandi-archive, e.g. `validators/d0.75.0-s0.12.0-n0.7.1-p3.1.0-h4.1.0-b2.1.0/`, holding a [pixi](https://pixi.sh) manifest (`pixi.toml`) and its lock file (`pixi.lock`).
- **What's pinned.** The lock pins conda-forge and PyPI packages with checksums: the six validator packages, plus git, git-annex, DataLad, datalad-container and con-duct (`duct`), which the worker uses to build the dataset and run validation (see [Validation job](#validation-job)). git and git-annex therefore come from the lock, at exact versions, rather than from the base image's operating-system packages, which can change whenever the base image is rebuilt.
- **Registries.** CI builds each image once and pushes it to GitHub Container Registry as `ghcr.io/dandi/dandi-validation:<version code>`, the canonical tagged copy. The same image is pushed to the worker app's Heroku registry to release it, and can be pulled anywhere else: Docker, Podman, or Apptainer on HPC (`apptainer pull docker://ghcr.io/dandi/dandi-validation:<version code>`). Heroku's registry doesn't keep version tags, so GHCR records which image produced each code.
- **Isolation.** The worker app holds no database, bucket or Django credentials: only the archive's URL and the worker token. It reads files through URLs the archive hands out and writes records through a presigned upload URL (see [Validation job](#validation-job)). A crafted file that exploits a parser bug can therefore reach at most the worker token, which only opens the job API.

<details>
<summary>Implementation</summary>

- **One shared Dockerfile.** `validators/Dockerfile` takes the code as a build argument (`--build-arg VERSION_CODE=<code>`) and has two stages:
  - **Build:** the official pixi image on Ubuntu (`ghcr.io/prefix-dev/pixi:<pixi version>-noble`) runs `pixi install --locked` in that directory.
  - **Runtime:** plain `ubuntu:24.04` receives only the installed environment, an activation script from `pixi shell-hook`, and the worker's small program (see [Validation worker app](#validation-worker-app)), which doesn't import Django. pixi itself isn't needed at runtime.

  Since the environment carries its own tools and libraries, the base image only has to provide the basics, such as glibc. Both base images are pinned by digest.
- **Code check.** At startup the worker derives its version code from the installed packages (`importlib.metadata`) and refuses to run if it differs from the code the image was built for.
- **Code table.** `VALIDATOR_CODES` and two small helpers that build and parse version codes live in a dependency-free module in dandi-archive, used by both the archive and the worker image:

  ```python
  #: One-letter code of each package in a version code, in the code's order
  VALIDATOR_CODES = {
      ValidatorType.dandi: "d",
      ValidatorType.dandischema: "s",
      ValidatorType.nwbinspector: "n",
      ValidatorType.pynwb: "p",
      ValidatorType.hdmf: "h",
      ValidatorType.bids_validator_deno: "b",
  }
  ```

- **Subprocess.** The worker runs validation as a subprocess (see [Validation job](#validation-job)), so `dandi validate -J` works and a crash or out-of-memory kill only ends that run. The subprocess doesn't receive the worker token.

</details>

### Version updates

New validator versions are picked up automatically; nobody edits a version string by hand.

1. **Daily scan.** A scheduled GitHub Actions workflow in dandi-archive runs once a day. It resolves the six validator packages unpinned against PyPI with pixi, which picks the newest plain releases that install together, and reads their versions from the resulting lock to compute the version code.
2. **Pull request.** If `validators/<code>/` doesn't exist yet, the workflow creates it with those versions pinned exactly, locks it, and opens a pull request with auto-merge enabled.
3. **Checks.** CI builds the image and runs a smoke test on a small fixture Dandiset. The pull request merges once they pass.
4. **Release.** On merge, the release workflow pushes the image to GHCR and to the worker app's Heroku registry, and releases it.
5. **Target.** The new image's first claim reports its code, and the archive makes it the target (see [Settings](#settings)).

<details>
<summary>Implementation</summary>

- **Sources.** The six validator packages come from PyPI (pixi's `[pypi-dependencies]`), matching what the scan reads; Python, git and git-annex come from conda-forge.
- **Plain releases only.** Pre-releases, dev releases and yanked releases are skipped, since version codes can only encode plain releases.
- **Immutable directories.** A code's directory is created once and never edited. The other tools in the lock (git, git-annex, DataLad, datalad-container, con-duct) are only re-resolved when a new code is created, so one code always names one image.
- **Incompatible releases.** If the newest releases can't be installed together, the resolver falls back to the newest set that can, so the scan never proposes a broken environment.

</details>

### Triggering

Validation jobs are rows of the summary table in the `queued` state (see [Summary table](#summary-table)). The archive creates them in two ways, both only once a target exists:

- **Manifest hook:** at the end of `write_manifest_files`, for drafts only. Publishing and some management commands also call it for published versions, so it checks `version.version == 'draft'`.
- **Reconciler:** a beat task every few minutes. It is what guarantees coverage, because checksums arrive after the manifests are written and the draft is not re-pended then. The hook only cuts latency.

A draft is eligible when all of these hold. Queuing is idempotent, and the job API checks them again when a job is claimed:

- every blob asset has a `sha256` and every Zarr is `COMPLETE`;
- it has no complete row for its required code and stored fingerprint, and no run is in progress.

Each run's state lives in its row (`queued`, `running`, `complete`, `failed` or `superseded`, with `requested_at`, `heartbeat_at` and `attempts`), and the reconciler re-queues runs whose heartbeat stopped. Published versions are never queued: their result is frozen at publication (see [Publication](#publication)), and versions published before this feature have none.

### Content fingerprint

The fingerprint is a dataset-level checksum of the version's `(path, digest)` pairs. `digest` is the blob's DANDI etag (`AssetBlob.etag`) or the Zarr checksum (`ZarrArchive.checksum`). Zarr assets are included because layout and BIDS checks still see their paths, even though their content is not checked. Dandiset-level metadata is excluded, because the archive already validates it independently.

- **Updated in O(1).** The fingerprint is a multiset hash, so each asset change updates it in constant time instead of rehashing every asset.
- **Pairing.** Each result is stored with the fingerprint and version code it was produced for. A draft needs a run only when no complete result exists for its current fingerprint and required code; otherwise the existing result applies as is.
- **Why.** The draft can change while a run is in progress. The job records the fingerprint of the snapshot it validated, and on completion keeps the result only if the draft still has that fingerprint.

<details>
<summary>Implementation</summary>

- **How.** Each `(path, digest)` pair is hashed to an element. The version stores the element-wise sum of its pairs' elements as its fingerprint state, and the fingerprint is the SHA-256 of that state.
- **Where.** Adding an asset adds its element, removing one subtracts it, and replacing one does both. Every asset change goes through `_add_asset_to_version` and `_remove_asset_from_version` (`services/asset/`), which update the state in the same transaction. When a Zarr's checksum changes on ingestion, its entry is replaced the same way. The etag is known at upload, so the later arrival of `sha256` does not change the fingerprint.
- **Construction.** Use a multiset hash with a large state, such as LtHash (1024 16-bit lanes, 2 KB; Lewi et al., 2019). A plain sum of SHA-256 digests modulo 2^256 is cheaper, but generalized-birthday attacks make it practical to craft a set of files that collides with another.
- **Backfill.** Existing versions get a one-off O(n) computation. The same management command can recompute any version from scratch to check for drift.

</details>

### Required versions

Each draft stores its required version code in a new `Version` column, next to its content fingerprint.

- **Moved on file changes.** Whenever an asset change updates the fingerprint (an asset was added, removed or replaced), the same update sets the required code to the current target. A draft therefore moves to newer validators only when its files change.
- **Kept on metadata-only changes.** A metadata-only change leaves the fingerprint, and so the required code, unchanged. The draft keeps its result, needs no new run, and is never blocked by checks added later.
- **Frozen at publication.** Published versions copy both columns from the draft and never change them. Publication requires `validatedBy: true`, so a published version's result is always a passing one.
- **Unset.** Drafts without a required code get the current target as soon as one exists.
- **Retired codes.** If a draft's required code is not the code of the deployed worker image and the draft has no complete row for it (for example, its run failed before a new image was released), the draft moves to the current target.

### No caching across jobs

Per-asset results are not kept from one job to the next, because an asset's result can depend on other files. For example, if a video file's path changes without updating the `ImageSeries` that points to it, the NWB file itself becomes invalid even though its own content is unchanged.

So every job validates the whole Dandiset, and the content fingerprint covers every path and checksum in it. A change to any file therefore invalidates the whole record, while metadata-only changes don't.

### Validation job

The work is split between the archive and the worker app.

1. **Claim (archive).** The worker calls the claim endpoint with its version code. The archive marks the oldest queued job for that code as running, and returns the draft's stored fingerprint, its assets with download URLs, and presigned upload URLs for the results.

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
   - **On Heroku**, the dyno already runs the validator image, so the dataset registers it with a call format of `{cmd}` and a small image file holding the image's GHCR reference and digest. The command then runs in place.
   - **Elsewhere**, the same command registers the real image, e.g. `datalad containers-add dandi-validation --url docker://ghcr.io/dandi/dandi-validation:<version code>` (which builds an Apptainer image), and runs inside it.
   - **`duct`** (con-duct) captures stdout, stderr and resource usage: peak memory, CPU and wall time (`info.json`, `usage.jsonl`).

   </details>
4. **Process the results (worker).** Infrastructure failures are retried and, if they persist, the job is reported as failed rather than counted as content errors. A run is complete when every NWB and BIDS file has an outcome. Zarr-backed assets (NWB or BIDS stored as Zarr) are counted as "not checked" for now (see [Open questions](#open-questions)).

   <details>
   <summary>Implementation</summary>

   - relativize paths, strip URLs (presigned URLs carry credentials), drop `DANDI.FILE_CONTENT_STREAMED`, and group pynwb results under a fixed ID;
   - exclude results for `dandiset.yaml`, since the archive validates metadata itself;
   - retry, with backoff, files whose results are `INTERNAL`-origin, `DANDI.FILE_CONTENT_MISSING` or streamed-read failures. If they keep failing, report the job as failed: the row becomes `failed` with `success` left empty, and Sentry is notified.

   </details>
5. **Report (worker).** Upload the JSONL and the provenance file to the presigned URLs, then call the complete endpoint with the counts, top issues, checked/not-checked counts, and duct's peak memory and wall time. The worker sends heartbeats throughout the run, and afterwards deletes the temporary dataset and dandi-cli's cache.
6. **Store (archive).** Only `ERROR` and `CRITICAL` results block publication: for a complete run, `success` is true when there are none. The archive applies this policy, not the worker. If the draft changed during the run, the result is superseded and the reconciler queues a new run; otherwise the draft is stamped (see [Stamping](#stamping)). The draft is never set back to `PENDING`.

   <details>
   <summary>Implementation</summary>

   `success` is `counts.CRITICAL + counts.ERROR == 0`. dandi-cli maps validator severities onto its own as follows:
   - NWB Inspector: `CRITICAL` → `ERROR`, best-practice violations → `WARNING`, suggestions → `HINT`.
   - BIDS validator: errors → `ERROR`, warnings → `HINT`.

   Under `select_for_update`, the archive compares the draft's stored fingerprint with the job's. If it changed, the row is marked `superseded`; otherwise it is marked `complete` and the draft is stamped.

   </details>

### Summary table

Each validation run is a row in a new `VersionValidationSummary` table, which also serves as the job queue.

<details>
<summary>Implementation</summary>

```python
class VersionValidationSummary(TimeStampedModel):
    version = models.ForeignKey(
        Version, related_name='validation_summaries', on_delete=models.CASCADE
    )
    validators = models.CharField(max_length=255)  # version code
    content_fingerprint = models.CharField(max_length=64)
    state = models.CharField(max_length=10)  # queued, running, complete, failed, superseded
    success = models.BooleanField(null=True)  # set only for complete runs
    summary = models.JSONField()  # counts, top issues, checked/not-checked counts, record path, resource usage, archive version
    requested_at = models.DateTimeField()
    heartbeat_at = models.DateTimeField(null=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['version', 'validators', 'content_fingerprint'],
                name='unique-version-validators-fingerprint',
            )
        ]
```

</details>

- **One row per run target.** Rows are keyed by version, version code and fingerprint, so queuing a run for new content doesn't erase the last result. Only the row for the Version's required code and fingerprint affects publication; rows for other codes are informational.
- **Provenance.** Each row's summary records the archive release (`importlib.metadata.version('dandiapi')`) that produced it.
- **History.** Rows and their records are never deleted, so every past result, including superseded ones, stays available.
- **Admin.** The table is registered in Django admin, so staff can review rows.

### Record storage

Full JSONL records go in the archive bucket at:

```
dandisets/{id}/validation/{code}/{fingerprint}.jsonl
dandisets/{id}/validation/{code}/{fingerprint}.provenance.json
```

The provenance file holds the `datalad containers-run` record and duct's `info.json`.

- **Immutable by construction.** The path is determined by the content and the validator versions, so it never needs pinning to an object version.
- **Shared.** The path leaves out the version, so a draft and the version published from it share the same object.
- **Upload and embargo.** The worker uploads each record through the presigned URL in its job. The archive signs that URL with the `embargoed` tag when needed, because the bucket is otherwise publicly readable, and removes the tag at unembargo.

<details>
<summary>Implementation</summary>

- Pinning to an object version wouldn't work anyway, since the lifecycle rule deletes older noncurrent versions under `dandisets/`.
- At unembargo, tags are removed by listing the `dandisets/{id}/validation/` prefix, since the existing helper only covers the five fixed manifest paths.

</details>

### Stamping

A shared helper, `stamp_validation_fields(version)`, is called by `validate_version_metadata` and when a job is stored. The latter calls it only when the draft is `VALID` or `INVALID`: a `PENDING` or `VALIDATING` draft is stamped by the normal path, and a `PUBLISHING` or `PUBLISHED` draft is never touched.

- **No timestamp change.** Stamping doesn't bump `Version.modified` when only these two fields change, so the "Last update" date only moves for real content changes (see also [#2950](https://github.com/dandi/dandi-archive/pull/2950)).
- **Gating.** Draft validation is publish-time validation (see [Current state](#current-state)). So whenever `validatedBy` is not `true`, the new schema rule produces an ordinary validation error on `validatedBy`, and the draft becomes `INVALID`. The existing publish gating handles the rest, and **the publish service needs no new check**.
- **Owners can't set them.** `Version.strip_metadata` adds both fields to its computed fields, so owners cannot set them through the metadata editor or the API.

<details>
<summary>Implementation</summary>

```python
def _validation_fields(version: Version) -> dict | None:
    if not settings.DANDI_VALIDATION_GATING or version.required_validators is None:
        return None  # remove both fields
    row = version.validation_summaries.filter(
        validators=version.required_validators,
        content_fingerprint=version.content_fingerprint,
        state='complete',
    ).first()
    passed = row.success if row else None  # None: no complete record for this content yet
    return {
        'validatedRequiredVersions': parse_version_code(version.required_validators),
        'validatedBy': passed,
    }
```

- **Writes.** The helper merges the fields into the draft's metadata, re-runs schema validation, and writes `status`, `validation_errors` and `metadata` with `.update()`. It does not bump `Version.modified` when the only metadata change is to these two fields. Today `validate_version_metadata` always sets `modified=now`, which would move the "Last update" date on every result even though the content didn't change. Content changes already bump `modified` themselves (see also [#2950](https://github.com/dandi/dandi-archive/pull/2950)).
- **Concurrency.** The concurrent `aggregate_assets_summary` task already uses optimistic concurrency on `metadata`, so it retries if stamping changed the metadata underneath it.

</details>

### Publication

The published Version inherits both fields from the draft's metadata, and the draft's fingerprint and required code. Published metadata is immutable, so the published Version stays tied to those validator versions permanently. `_publish_dandiset`'s final `validate(..., 'PublishedDandiset')` enforces the rule a second time.

Publishing also copies the draft's complete row for the required version code to the new published Version. The content is identical, so the fingerprints match by construction and the record object is shared. The published Version's banner shows the result straight away, and its content is never validated twice.

### Read API

There are no separate validation endpoints. `VersionDetailSerializer`, the `/versions/{version}/info/` payload the landing page already loads, applies the existing embargo check and gains:

- **`validation_summary`:** the complete row for the Version's required code and fingerprint. For versions without a required code, it is the newest complete row, and it is `null` if there is none.
- **`validation_run`:** the state of the current run, if any: queued, running (n of m files), or failed.
- **`stale`** (drafts only): set when the summary's fingerprint differs from the draft's current one.

Both metadata fields also appear in the raw metadata at `GET /api/dandisets/{id}/versions/{version}/`.

### Management commands

A `revalidate_content` command does two things:

- **`--force`** marks a version code's rows `superseded`, so the reconciler re-runs them, for example after a fix to the worker.
- **Override** sets a row's `success` and writes an admin audit record.

### Search

Free-text search leaves out the two fields, so searches for "pynwb" or "hdmf" don't match every stamped version.

<details>
<summary>Implementation</summary>

Free-text search casts the whole metadata to text (`Cast('metadata', TextField())` in `views/dandiset.py`). Remove the two fields with the jsonb `-` operator before the cast.

</details>

### Job API

A small API lets the worker app claim jobs and report results. It authenticates with `DJANGO_DANDI_VALIDATION_WORKER_TOKEN`, a bearer token checked by its own permission class rather than a user account, and these endpoints are all the token opens.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/validation/jobs/claim/` | Claim the oldest queued job for the worker's version code; returns the job, or nothing |
| `POST` | `/api/validation/jobs/{id}/heartbeat/` | Keep a running job alive |
| `POST` | `/api/validation/jobs/{id}/complete/` | Report the summary after uploading the record |
| `POST` | `/api/validation/jobs/{id}/fail/` | Report a run that could not complete |

### Validation worker app

- **Process.** One process per dyno loops: claim a job, run it, report it, repeat, sleeping briefly when nothing is queued. Capacity scales with the number of dynos.
- **Restarts.** Heroku restarts dynos at least daily and on every release. An interrupted job stops sending heartbeats, and the reconciler re-queues it.
- **Time limit.** Each job has a time limit, after which the worker reports it as failed.
- **No broker.** The worker app doesn't use Celery or the archive's CloudAMQP broker; the summary table is the queue.

### Frontend

- **Banner** at the top of `DandisetMain.vue`, driven by `/info/`:
  - "Content validation queued", "Running (n of m files)", or "Could not complete — staff notified";
  - error styling if errors were found, warning styling if only warnings were found, and a small "validated" chip if it passed;
  - text naming the validators and their versions;
  - "results predate the latest changes" when `stale`;
  - "Zarr assets not checked" when applicable.
- **Pending, not error.** While `validatedBy` is `null`, its validation error is shown as pending, not counted in the error total, and the Publish button says "Waiting for content validation". The page polls `/info/` while a run is queued or running.
- **Details:** this opens `ValidationErrorDialog.vue` with a new tab built from `top_issues`, plus a link to the full record. Each issue maps to the dialog's existing `{field, message, path}` shape, so grouping by path works unchanged.
- **Validation error:** add an entry for `validatedBy` to `VALIDATION_ICONS`, with a clearer message.

## dandi-infrastructure

- **Worker app.** A new Heroku app (and a staging counterpart) on the container stack, sized from the pilot. Its config vars are only the archive's API URL, the worker token and a Sentry DSN.
- **Archive config vars.** `DJANGO_DANDI_VALIDATION_GATING` and the worker token as a secret. There is no version string to maintain: the target comes from the released worker image (see [Version updates](#version-updates)).
- **Releases.** CI pushes each image to GHCR and to the worker app's Heroku registry, and releases it there, using a Heroku API key stored as a GitHub Actions secret.
- **No storage changes.** Records go in the existing bucket through presigned URLs the archive already knows how to sign.

<details>
<summary>Implementation</summary>

- **Worker app:** a `heroku_app` resource with `stack = "container"`, and a `heroku_formation` for its `worker` process (`standard-2x` has only 1 GB of memory), quantity 0 until the pilot.
- **Archive config vars:** add the gating variable under `# DANDI-specific variables` in `terraform/api.tf`, and in `staging.tf` if staging should validate too. Add `DJANGO_DANDI_VALIDATION_WORKER_TOKEN` to `sensitive_config_vars`, from the same Terraform variable as the worker app's token:

```hcl
DJANGO_DANDI_VALIDATION_GATING = "true"
```

</details>

## dandi-cli

- **Release the streaming stack** ([#1955](https://github.com/dandi/dandi-cli/pull/1955), [#1956](https://github.com/dandi/dandi-cli/pull/1956), [#1957](https://github.com/dandi/dandi-cli/pull/1957)). It currently depends on datalad-fuse by git URL, which PyPI rejects, so it needs a datalad-fuse release with the remfile backend first.
- **Classify streamed-read failures as `INTERNAL`**, so the archive can tell them apart from content errors without matching message text.
- **Record hdmf's version.** pynwb validation runs on hdmf, but records only carry pynwb's version, because dandi-cli has no `hdmf` validator. Add an optional `Origin` field for the versions of libraries a validator depends on (bumping `record_version`), and fill it with hdmf's version in pynwb and NWB Inspector records.
- **NWB Inspector version.** Every NWB Inspector record currently reports `validator_version: ""`, because the cache in `_get_nwb_inspector_version` (`dandi/files/bases.py`) starts as `""` and is checked with `is not None`. The worker reads versions from its image, so this is now a consistency fix rather than a prerequisite.
- **Absolute paths.** Records contain absolute local paths. The archive relativizes them for now, and a CLI option can come later.
- **Unstable IDs and wrong `dandiset_path`.**
  - pynwb result IDs embed the error message (`pynwb.<message>`), so the archive groups them under a fixed ID when building `top_issues`.
  - NWB Inspector results set `dandiset_path` to the file's parent directory instead of the Dandiset root.

## Publication latency (accepted trade-off)

After a content change, the owner can publish only once the worker has validated the new content: the queue wait plus a full validation of the Dandiset (see [No caching across jobs](#no-caching-across-jobs)). Embargoed drafts are validated too, and their record carries over at unembargo because the fingerprint doesn't change, so publishing right after unembargo is not delayed. This delay is accepted in exchange for publishing only validated content.

The archive monitors the delay so a stalled worker is noticed:

- **Daily check.** A daily task emails `DANDI_DEV_EMAIL` with each draft that has waited more than three days for a result, and how long it has waited. Embargoed drafts are listed in a separate section, since they don't block owners yet.

  <details>
  <summary>Implementation</summary>

  The task is a beat task scheduled like `send_pending_users_email`. It selects:
  - runs queued or running for more than three days since `requested_at`, failed runs, and runs whose heartbeat stopped;
  - as a fallback, drafts that were never queued: no row for their required code and stored fingerprint, and `modified` older than three days.

  </details>
- **Alerts.** Sentry reports errors from both apps, and an alert fires when the number of queued jobs grows past a threshold.

## Old files vs. new checks (accepted trade-off)

Once a draft's files change, the whole Dandiset is validated with the latest validation target, so files carried over from earlier releases are re-checked with the latest validators. A small content change, such as adding one file, could therefore be blocked by a check that did not exist when the other files were published. This is accepted, because it means content and structure enhancements go hand-in-hand.

Metadata-only changes are not affected: a draft keeps the validator versions and result from its last file change (see [Required versions](#required-versions)).

# Lifecycles

**Draft with changed files.**

1. The owner changes the draft's files. The same change updates the fingerprint and moves the draft's required versions to the current target, and the draft goes `PENDING`.
2. Metadata validation stamps the required versions and sets `validatedBy = null`. The draft becomes `INVALID` with the error "`validatedBy` is `None`: content validation with … has not finished for the current files, and it must pass before publishing", which the UI shows as "Content validation queued".
3. The manifest hook queues validation, or the reconciler does once every checksum exists.
4. The run completes. If the draft still has the same fingerprint, the row is stored and the draft is stamped:
   - if it has no errors, `validatedBy = true` and the draft becomes `VALID`, so it can be published;
   - if it has errors, `validatedBy = false`, and the banner and dialog list them.

   If the draft changed during the run, the row is superseded and the reconciler queues a new run.

**Metadata-only edit.**

1. The owner edits only the draft's metadata, and it goes `PENDING`.
2. The fingerprint is unchanged, so the draft keeps its required versions and result. No run is queued.
3. If that result passed, the draft becomes `VALID` straight away and can be published, even if the target has moved on since.

**New validator release.**

1. A new release of one of the six packages appears on PyPI.
2. The next daily scan opens a pull request adding the new code's directory, and it merges once its checks pass.
3. The release workflow releases the new image to the worker app, and its first claim makes the new code the target.
4. Drafts keep their required versions until their files next change, so nothing is re-validated and publication is not interrupted. Drafts still waiting on a run under the old code move to the new target (see [Required versions](#required-versions)).

Published versions keep their frozen validator versions.

# Rollout

1. **dandi-schema:** add `ValidatorType`, the two fields and the publication rule, then bump the version and release.
2. **datalad-fuse:** release with the remfile backend.
3. **dandi-cli:** release with the streaming stack, the `INTERNAL` classification, hdmf's version in records and the NWB Inspector fix.
4. **dandi-archive:** upgrade dandischema and run `migrate_version_metadata --all`. Ship the table, the fingerprint state, fingerprint and required-code columns with their backfill, job API, reconciler, worker program and image build, stamping, publish-time copy, `/info/` fields, banner and daily check, plus the daily version scan and the release workflow, with gating off.
5. **dandi-infrastructure:** add the worker app and its formation, and the token on both apps, staging first.
6. **Pilot** on a small, a BIDS and a large Dandiset, using duct's summaries. Measure seconds per file, peak memory, bytes read, worker start time, the fingerprint backfill time, how long re-validating the largest Dandiset takes after a one-file change, and how long the largest Dandiset takes compared with Heroku's daily dyno restart. Then choose the dyno size and count.
7. **Shadow mode:** release the first image to the worker app with gating off. Its first claim sets the target, and existing drafts get it as their required versions. Results and the banner appear, but publication is not gated.
8. **Sweep** every draft. Published versions are not validated: their results are frozen at publication. Either scale the worker app up temporarily, or run the same image elsewhere, for example with Apptainer on HPC near the bucket, against the same job API; estimate the cost first.
   - **Capacity:** `files × seconds per file ÷ processes`. For example, 500k files at 30 seconds each is about 170 process-days, or about 11 days with 16 processes.
   - **Regions:** Heroku's US region runs in AWS us-east-1, while the bucket is in us-east-2.
9. **Review:** when the majority of records are available, review them for accuracy and summarize potential effects and performance.
10. **Turn gating on**, then set drafts to `PENDING` so they are stamped. The existing `revalidate --versions` management command cannot do this as is: `validate_version_metadata` returns early unless a version is `PENDING`, so the command must first set them `PENDING`.

# Alternatives to consider

- **A dedicated publish check in the archive instead of a schema rule.** This would need changes to `Version.publishable` and `_lock_dandiset_for_publishing`, a new exception, and frontend gating, all of which the schema rule reuses. The schema rule also makes the requirement visible to anyone validating DANDI metadata.
- **An external trusted runner (the previous design).** A runner on separate compute would validate the `dandisets/` DataLad clones and push summaries through a staff-only endpoint. It was not chosen because the backup lag adds publication latency and it cannot read embargoed content. The chosen design keeps its isolation, but takes its inputs from the archive.
- **Validators inside the archive app.** Running the validators as a subprocess on a worker dyno of the archive's own app avoids a second app and the job API. But that dyno holds the database, bucket and Django credentials, and it must carry every validator environment.
- **Store full records in the archive database.** They are large, and it would tie the archive to dandi-cli's record model, which rejects unknown enum values.
- **A richer provenance object**, e.g. a `ValidationActivity(Activity)` with `Software` entries in `wasAssociatedWith`, mirroring `publishedBy: PublishActivity`. It is more expressive, but the map and boolean are simpler to look up and to enforce in `check_publication_status`.

# Open questions

1. **Worker size and sweep budget.** Which dyno size and count, and where should the initial sweep run (the worker app scaled up, or the same image elsewhere)? To be decided from the pilot.
2. **Retry thresholds.** How many retries, and how much backoff, before a run is marked failed?
3. **Zarr.** Every asset should be NWB or BIDS, and either can be stored as Zarr. Zarr-backed assets are reported as "not checked" for now. Should validation include them?
