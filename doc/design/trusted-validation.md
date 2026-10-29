# Trusted File and Dataset Validation

Authors: Cody Baker

Status: proposal

# Contents

- [Overview](#overview)
  - [Goals](#goals)
  - [Non-goals](#non-goals)
  - [Summary](#summary)
- [Terminology](#terminology)
- [Current state](#current-state)
- [Proposed solution](#proposed-solution)
  - [dandi-schema](#dandi-schema)
  - [dandi-archive](#dandi-archive)
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
  - **Drafts:** the latest set the archive is configured for.
  - **Published versions:** the set frozen at publication, so later validator releases never make them invalid.
- Errors and warnings are shown to everyone in a banner on the Dandiset landing page ([#1486](https://github.com/dandi/dandi-archive/issues/1486)). Warnings do not block publication but reflect overall quality.
- Changes only to the metadata of previously published versions should not trigger version bumps for dataset validation.

## Summary

Today the archive only validates simple asset metadata, not content or dataset layout: each Asset's metadata is compared against the `PublishedAsset` schema, and the draft Version's metadata against the `PublishedDandiset` schema.

Neither the archive backend nor any external service runs the validators that check the *contents* of files nor the *layout* of datasets: NWB Inspector, PyNWB validation, BIDS validator, or even the ad-hoc DANDI layout enforced by CLI command `dandi validate`. As a result, Dandisets with invalid NWB files or BIDS/DANDI layouts can be published (e.g. [#2412](https://github.com/dandi/dandi-archive/issues/2412)).

This document proposes running `dandi validate` inside the archive, in a dedicated Celery worker, over every Dandiset version, more than 2 PB in total. After a draft's asset manifests are written, the worker builds a DataLad dataset from the version's assets and streams validation through dandi-cli's datalad-fuse support ([dandi/dandi-cli#1955](https://github.com/dandi/dandi-cli/pull/1955), [#1956](https://github.com/dandi/dandi-cli/pull/1956), [#1957](https://github.com/dandi/dandi-cli/pull/1957)).

- **Results:** each Version's metadata gets two fields: the exact validator versions its result must come from, and whether that result passed. A summary of each result goes in a new table, and the full record goes in the archive bucket.
- **Gating:** the archive blocks publication unless that result has no errors.

The changes in each repository are small:

| Repository | Change |
|---|---|
| dandi-schema | A `ValidatorType` enum, two read-only `Dandiset` fields, one publication rule, one schema version bump |
| dandi-archive | One table, a validation task with a scheduler, a worker process type, validator environments built from lock files, a few lines in draft validation and publishing, `/info/` fields, a banner, a daily check |
| dandi-infrastructure | Two config vars and one worker formation |
| dandi-cli | A release with the streaming stack and small fixes |
| datalad-fuse | A release with the remfile backend, so dandi-cli can depend on it |

# Terminology

- **Validator versions:** the map from each package that affects validation results to the exact version used to produce a record. Keys are plain distribution names, and all six are always present:

  ```json
  {"dandi": "0.75.0", "dandischema": "0.12.0", "nwbinspector": "0.7.1", "pynwb": "3.1.0", "hdmf": "4.1.0", "bids-validator-deno": "2.1.0"}
  ```

  - **Source:** all six are read from the validator environment that produced the record (see [Validator environments](#validator-environments)). `dandischema` here is that environment's dandischema, not the archive's own dandischema library or the metadata's `schemaVersion`.
  - **Sanity check:** every key except `hdmf` also appears in each record's `origin.validator_version`.
- **Version code:** a short, readable string form of a validator-versions map. It names the validator environment's lock file, the archive's setting, and the record's path in the bucket. A container tagged with the code can reproduce records outside the archive.
  - **Form:** each package's one-letter code (see `VALIDATOR_CODES` under [Validator environments](#validator-environments)) followed directly by its version, in the code table's order, with no separator between entries. For the map above: `d0.75.0s0.12.0n0.7.1p3.1.0h4.1.0b2.1.0`.
  - **Parsing:** each entry matches `([a-z])(\d+(?:\.\d+)*)`, and a whole code matches `(?:[a-z]\d+(?:\.\d+)*)+`.
  - **Why this is unambiguous:** codes are single letters, and versions must be plain releases made only of digits and periods (e.g. `0.75.0`). A pre-release, post-release, dev or local version (e.g. `1.0rc1`, `0.75.0+12.gabc`) cannot be encoded. The fixed order means equal maps always give identical codes.
- **Validation target:** the version code drafts must currently be validated with (see [Settings](#settings)).
- **Content fingerprint:** a hash of the files a version contains (see [Content fingerprint](#content-fingerprint)).

# Current state

These are the parts of the archive this design builds on.

- **Version status and publishing.** `Version.status` reflects *Dandiset metadata* validation only. `Version.publishable` requires `status == VALID` and every asset `VALID`, and `_lock_dandiset_for_publishing` refuses to publish otherwise.
- **Draft validation is publish-time validation.** `validate_version_metadata` (`dandiapi/api/services/metadata/`) does three things:
  - it builds the would-be published metadata with `_build_publishable_version_from_draft`, which injects `datePublished` and `publishedBy`;
  - it validates that metadata against `PublishedDandiset`;
  - it stores the outcome in `Version.status` / `Version.validation_errors`.

  Any rule dandischema enforces on *published* Dandisets therefore already marks the draft `INVALID`. That blocks re-publishing at a later time, and the UI shows the error in its existing validation dialog.
- **When validation runs.** Every change to a draft (adding or removing assets, editing metadata, unembargoing, Zarr ingestion) sets the draft to `PENDING`. A beat job (`validate_draft_version_metadata`, every `DANDI_VALIDATION_JOB_INTERVAL` seconds) then queues metadata validation, the assets summary, and `write_manifest_files` for it. Publishing also writes manifests for the new published version.
- **Checksums arrive later.** A new blob's `sha256` is computed later on the `checksum-worker` dyno. When its asset then validates, the draft's `modified` is bumped, but the draft is not set back to `PENDING`.
- **Publishing copies the draft's metadata.** `_build_publishable_version_from_draft` deep-copies the draft's metadata into the new published Version. Published metadata is immutable.
- **Server-computed fields** such as `assetsSummary` are removed from user-supplied metadata by `Version.strip_metadata`.
- **Dynos.** The `Procfile` defines `web`, `worker` (the default queue, which also runs beat, so its tasks must stay lightweight) and `checksum-worker`. The settings package enables `CELERY_TASK_ACKS_LATE` and a prefetch multiplier of 1 for every task.
- **Bucket.** Objects are publicly readable except those tagged `embargoed=true`, and the archive's IAM user can read embargoed objects too. Under `dandisets/`, a lifecycle rule keeps only the newest noncurrent version of each object and deletes older ones after a day.

# Proposed solution

## dandi-schema

Add a `ValidatorType` enum and two read-only fields to `Dandiset`. Map-valued fields keyed by an enum already exist (`BareAsset.digest: Dict[DigestType, str]`).

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

`validatedBy` has three states:

| Value | Meaning |
|---|---|
| `null` | Not run: no complete record exists yet for the current content. This covers queued and running validation, and runs that could not complete. |
| `false` | Failed: the record has at least one `ERROR` or `CRITICAL` result. |
| `true` | Passed. |

Extend `Dandiset.check_publication_status`, inside the branch for published Dandisets (the one where `datePublished` is set):

```python
if self.validatedRequiredVersions is not None and self.validatedBy is not True:
    err(
        "validatedBy",
        "a validation record without errors, produced with validatedRequiredVersions, "
        "is required to publish",
    )
```

The rule only applies when `validatedRequiredVersions` is set. Already-published metadata, which lacks the field, stays valid, and archive instances that don't enable the feature are unaffected.

**JSON-LD.** Plain distribution names are not JSON-LD terms. `dandi` would collide with the `dandi:` prefix in the `@context`, and the other keys would be dropped when the metadata is expanded. `generate_context` has no path for this today, so it needs an explicit branch, like the existing one for `digest`, that emits `{"@id": "dandi:validatedRequiredVersions", "@type": "@json"}`. JSON-LD then treats the whole map as a single JSON literal.

The schema change also needs some housekeeping:
- bump `DANDI_SCHEMA_VERSION`, and add the previous version to `ALLOWED_INPUT_SCHEMAS` and `ALLOWED_TARGET_SCHEMAS`;
- make `migrate()` drop both fields unconditionally when downgrading below the new version. `SIMPLE_DOWNGRADES` raises on non-empty values, and `validatedBy` is never empty once stamped; the archive re-stamps both fields anyway.

## dandi-archive

### Settings

- **`DJANGO_DANDI_VALIDATION_ENABLED`** (boolean, off by default) turns the validation worker on. It gates the manifest hook and the reconciler (see [Triggering](#triggering)).
- **`DJANGO_DANDI_VALIDATION_TARGET`** holds the validation target as a version code, and only gates publication.
  - **Unset:** nothing is stamped, and stamping removes both fields from draft metadata, so publication is not gated.
  - **Set:** it must name an installed validator environment; otherwise the worker alerts.
  - **Exposed** as `validation_target` on `/api/info/`.

With the worker enabled and the target unset, the archive runs in shadow mode: results and the banner appear, but publication is not gated.

### Validator environments

- **Lock files.** Each validator environment is a lock file committed in dandi-archive and named by its version code, e.g. `validators/d0.75.0s0.12.0n0.7.1p3.1.0h4.1.0b2.1.0.txt`. The committed lock files are the installed environments; removing an environment means deleting its lock file.
- **Built at startup.** When a validation worker dyno starts, it builds each environment with `uv pip sync --require-hashes` into a virtualenv on the dyno's disk. The slug and the `web` dyno don't carry them (each is about 157 MB compressed). The worker takes no tasks until every build and the code check pass, and a failed build alerts.
- **Code check.** The worker derives each environment's version code from what is actually installed (`importlib.metadata` inside the virtualenv) and refuses to use an environment whose code differs from its lock file's name.
- **Code table.** `VALIDATOR_CODES` and two small helpers that build and parse version codes live in dandi-archive, the only place that uses them:

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

- **Subprocess.** The task runs `dandi validate` as a subprocess from the environment. The archive's own dandischema pin therefore stays independent of the validators, `dandi validate -J` works (its process pool doesn't run inside a Celery child), and a crash or out-of-memory kill only ends the subprocess.
- **Isolation.** The subprocess environment drops `DATABASE_URL`, `AWS_*`, `DJANGO_*` and other secrets, but keeps `HOME`/`DANDI_CACHE` so dandi-cli's per-file cache on the dyno disk is used. It runs with memory and CPU limits, the parent process is non-dumpable, and results come back as JSONL on stdout. Only the parent writes to the database or the bucket. A crafted file that exploits a parser bug still runs on the same dyno (see [Open questions](#open-questions)).
- **Fallback.** If the pilot shows that building environments at startup is infeasible, use a single environment in the slug and accept a waiting window when the target changes.

### Triggering

Validation is queued on a dedicated `validation` queue in two ways, both only while the worker is enabled:

- **Manifest hook:** at the end of `write_manifest_files`, for drafts only. Publishing and some management commands also call it for published versions, so it checks `version.version == 'draft'`.
- **Reconciler:** a beat task every few minutes. It is what guarantees coverage, because checksums arrive after the manifests are written and the draft is not re-pended then. The hook only cuts latency.

A draft is eligible when all of these hold, and the task checks them again first, so duplicate requests are no-ops:

- it is not `PENDING` or `VALIDATING`, since its stored fingerprint may be stale until metadata validation runs;
- every blob asset has a `sha256` and every Zarr is `COMPLETE`;
- some installed environment has no complete row for the draft's stored fingerprint, and no run is in progress. Environments are run with the target first.

Each run's state lives in its row (`queued`, `running`, `complete`, `failed` or `superseded`, with `requested_at`, `heartbeat_at` and `attempts`), and the reconciler re-queues runs whose heartbeat stopped. Published versions are never queued: their rows are copied at publication (see [Publication](#publication)), and versions published before this feature are handled by the sweep (see [Rollout](#rollout)).

### Content fingerprint

The fingerprint is the SHA-256 of the sorted list of `(path, digest)` pairs for the version's assets. `digest` is the blob's DANDI etag (`AssetBlob.etag`) or the Zarr checksum (`ZarrArchive.checksum`). Zarr assets are included because layout and BIDS checks still see their paths, even though their content is not checked. Dandiset-level metadata is excluded, because the archive already validates it independently.

- **Stored.** `validate_version_metadata`, which runs after every content change, computes it and stores it in a new `Version` column. Existing versions are backfilled, or computed when the column is null. The etag is known at upload, so the later arrival of `sha256` does not change it. Hashing must fit within that task's `soft_time_limit` of 30 seconds; the pilot measures it on the largest draft.
- **Why.** The draft can change while a run is in progress. The task records the fingerprint of the snapshot it validated, and on completion keeps the result only if the draft still has that fingerprint.

### Validation task

1. **Snapshot.** In one transaction, read the draft's assets and its stored fingerprint.
2. **Build the DataLad dataset** in a temporary directory from that snapshot:
   - annex keys `SHA256E-s{size}--{sha256}{ext}` registered with `git annex fromkey` and `registerurl --batch`;
   - only direct S3 URLs, never the API download URL, presigned for embargoed blobs with an expiry at least as long as the task's time limit;
   - small text files (`dataset_description.json`, sidecar `.json`/`.tsv`, `README`, `.bidsignore`) committed to git;
   - Zarr paths present, since an empty directory would be skipped;
   - a minimal `dandiset.yaml` with non-empty `identifier`, `name` and `description` and no `schemaVersion`;
   - no FUSE mount, and git-annex from its PyPI wheel.
3. **Validate** with `dandi validate --missing-file-content=stream --min-severity INFO -f json_lines`, in each environment that needs a row, target first.
4. **Process the results:**
   - relativize paths, strip URLs (presigned URLs carry credentials), drop `DANDI.FILE_CONTENT_STREAMED`, and group pynwb results under a fixed ID;
   - exclude results for `dandiset.yaml`, since the archive validates metadata itself;
   - retry, with backoff, files whose results are `INTERNAL`-origin, `DANDI.FILE_CONTENT_MISSING` or streamed-read failures. If they keep failing, the row becomes `failed` with `success` left empty, and Sentry is notified;
   - a run is complete when every NWB and BIDS file has an outcome. Zarr-backed assets (NWB or BIDS stored as Zarr) are counted as "not checked" for now (see [Open questions](#open-questions));
   - for a complete run, `success` is `counts.CRITICAL + counts.ERROR == 0`, so only `ERROR` and `CRITICAL` block publication. dandi-cli maps validator severities onto its own as follows:
     - NWB Inspector: `CRITICAL` → `ERROR`, best-practice violations → `WARNING`, suggestions → `HINT`.
     - BIDS validator: errors → `ERROR`, warnings → `HINT`.
5. **Store.** Upload the JSONL (see [Record storage](#record-storage)). Then, under `select_for_update`, compare the draft's stored fingerprint with the snapshot's. If it changed, mark the row `superseded` and leave re-queuing to the reconciler. Otherwise mark it `complete` and stamp the draft (see [Stamping](#stamping)). The draft is never set back to `PENDING`.

### Summary table

```python
class VersionValidationSummary(TimeStampedModel):
    version = models.ForeignKey(
        Version, related_name='validation_summaries', on_delete=models.CASCADE
    )
    validators = models.CharField(max_length=255)  # version code
    content_fingerprint = models.CharField(max_length=64)
    state = models.CharField(max_length=10)  # queued, running, complete, failed, superseded
    success = models.BooleanField(null=True)  # set only for complete runs
    summary = models.JSONField()  # counts, top issues, checked/not-checked counts, record path, archive version
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

- **One row per run target.** Rows are keyed by version, version code and fingerprint, so queuing a run for new content doesn't erase the last result. Only rows for the Version's `validatedRequiredVersions` affect publication; rows for other codes are informational and let the next target be computed ahead of time.
- **Provenance.** Each row's summary records the archive release (`importlib.metadata.version('dandiapi')`) that produced it.
- **Garbage collection.** Superseded draft rows, and their records, are deleted once a newer complete row exists. This is new code: the existing garbage collection only covers uploads and blobs.
- **Admin.** The table is registered in Django admin, so staff can review rows, including those for the next target.

### Record storage

Full JSONL records go in the archive bucket at:

```
dandisets/{id}/validation/{code}/{fingerprint}.jsonl
```

- **Immutable by construction.** The path is determined by the content and the validator versions, so it never needs pinning to an object version. Pinning wouldn't work anyway, since the lifecycle rule deletes older noncurrent versions under `dandisets/`.
- **Shared.** The path leaves out the version, so a draft and the version published from it share the same object.
- **Embargo.** Records are written with `_streaming_file_upload(embargoed=…)`, because the bucket is otherwise publicly readable. At unembargo, tags are removed by listing the `dandisets/{id}/validation/` prefix, since the existing helper only covers the five fixed manifest paths.

### Stamping

A shared helper, `stamp_validation_fields(version)`, is called by `validate_version_metadata` and by the validation task. The task calls it only when the draft is `VALID` or `INVALID`: a `PENDING` or `VALIDATING` draft is stamped by the normal path, and a `PUBLISHING` or `PUBLISHED` draft is never touched.

```python
def _validation_fields(version: Version) -> dict | None:
    target = settings.DANDI_VALIDATION_TARGET  # parsed map, or None
    if target is None:
        return None  # remove both fields
    row = version.validation_summaries.filter(
        validators=version_code(target),
        content_fingerprint=version.content_fingerprint,
        state='complete',
    ).first()
    passed = row.success if row else None  # None: no complete record for this content yet
    return {'validatedRequiredVersions': target, 'validatedBy': passed}
```

- **Writes.** The helper merges the fields into the draft's metadata, re-runs schema validation, and writes `status`, `validation_errors` and `metadata` with `.update()`. It does not bump `Version.modified` when the only metadata change is to these two fields. Today `validate_version_metadata` always sets `modified=now`, which would move the "Last update" date on every result even though the content didn't change. Content changes already bump `modified` themselves (see also [#2950](https://github.com/dandi/dandi-archive/pull/2950)).
- **Gating.** Draft validation is publish-time validation (see [Current state](#current-state)). So whenever `validatedBy` is not `true`, the new schema rule produces an ordinary validation error on `validatedBy`, and the draft becomes `INVALID`. The existing publish gating handles the rest, and **the publish service needs no new check**.
- **Owners can't set them.** `Version.strip_metadata` adds both fields to its computed fields, so owners cannot set them through the metadata editor or the API.
- **Concurrency.** The concurrent `aggregate_assets_summary` task already uses optimistic concurrency on `metadata`, so it retries if stamping changed the metadata underneath it.

### Publication

The published Version inherits both fields from the draft's metadata. Published metadata is immutable, so the published Version stays tied to those validator versions permanently. `_publish_dandiset`'s final `validate(..., 'PublishedDandiset')` enforces the rule a second time.

Publishing also copies the draft's complete row for the required version code to the new published Version. The content is identical, so the fingerprints match by construction and the record object is shared. The published Version's banner shows the result straight away, and its content is never validated twice.

### Read API

There are no separate validation endpoints. `VersionDetailSerializer`, the `/versions/{version}/info/` payload the landing page already loads, applies the existing embargo check and gains:

- **`validation_summary`:** the newest complete row for the Version's `validatedRequiredVersions`. For versions without that field, it is the newest complete row, and it is `null` if there is none.
- **`validation_run`:** the state of the current run, if any: queued, running (n of m files), or failed.
- **`stale`** (drafts only): set when the summary's fingerprint differs from the draft's current one.

Both metadata fields also appear in the raw metadata at `GET /api/dandisets/{id}/versions/{version}/`.

### Management commands

A `revalidate_content` command does two things:

- **`--force`** marks a version code's rows `superseded`, so the reconciler re-runs them, for example after a fix to the task.
- **Override** sets a row's `success` and writes an admin audit record.

### Search

Free-text search casts the whole metadata to text (`Cast('metadata', TextField())` in `views/dandiset.py`). Remove the two fields with the jsonb `-` operator before the cast, so searches for "pynwb" or "hdmf" don't match every stamped version.

### Validation worker

A new `Procfile` process type consumes only the `validation` queue:

```
validation-worker: REMAP_SIGTERM=SIGQUIT celery --app dandiapi.celery worker --loglevel INFO --without-mingle --without-heartbeat --without-gossip --queues validation --concurrency 1 --max-tasks-per-child 1
```

- **Acknowledgement.** The task sets `acks_late=False`, overriding the global setting. Only the database-backed reconciler re-queues work, so broker redelivery and RabbitMQ's `consumer_timeout` don't matter.
- **Time limit.** The task sets an explicit `soft_time_limit`.

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

- **Config vars.** Add `DJANGO_DANDI_VALIDATION_ENABLED` and `DJANGO_DANDI_VALIDATION_TARGET` under `# DANDI-specific variables` in `terraform/api.tf`, and in `staging.tf` if staging should validate too:

  ```hcl
  DJANGO_DANDI_VALIDATION_ENABLED = "true"
  DJANGO_DANDI_VALIDATION_TARGET  = "d0.75.0s0.12.0n0.7.1p3.1.0h4.1.0b2.1.0"
  ```

- **Formation.** Add a `heroku_formation` for `validation-worker` next to `api_checksum_worker`, sized from the pilot (`standard-2x` has only 1 GB of memory), with quantity 0 on staging until it is enabled.
- **No storage changes.** Records go in the existing bucket, which the archive can already write.

Bumping the target is a reviewed dandi-archive change that adds the new lock file, followed by the config var change.

## dandi-cli

- **Release the streaming stack** ([#1955](https://github.com/dandi/dandi-cli/pull/1955), [#1956](https://github.com/dandi/dandi-cli/pull/1956), [#1957](https://github.com/dandi/dandi-cli/pull/1957)). It currently depends on datalad-fuse by git URL, which PyPI rejects, so it needs a datalad-fuse release with the remfile backend first.
- **Classify streamed-read failures as `INTERNAL`**, so the archive can tell them apart from content errors without matching message text.
- **NWB Inspector version.** Every NWB Inspector record currently reports `validator_version: ""`, because the cache in `_get_nwb_inspector_version` (`dandi/files/bases.py`) starts as `""` and is checked with `is not None`. The archive reads versions from the environment, so this is now a consistency fix rather than a prerequisite.
- **Absolute paths.** Records contain absolute local paths. The archive relativizes them for now, and a CLI option can come later.
- **Unstable IDs and wrong `dandiset_path`.**
  - pynwb result IDs embed the error message (`pynwb.<message>`), so the archive groups them under a fixed ID when building `top_issues`.
  - NWB Inspector results set `dandiset_path` to the file's parent directory instead of the Dandiset root.

## Publication latency (accepted trade-off)

After a content change, the owner can publish only once the worker has validated the new content: the queue wait plus validation of the new files. Embargoed drafts are validated too, and their record carries over at unembargo because the fingerprint doesn't change, so publishing right after unembargo is not delayed. This delay is accepted in exchange for publishing only validated content.

The archive monitors the delay so a stalled worker is noticed:

- **Daily check.** A beat task, scheduled like `send_pending_users_email`, emails `DANDI_DEV_EMAIL` with each affected Dandiset and how long it has waited. It selects:
  - runs queued or running for more than three days since `requested_at`, failed runs, and runs whose heartbeat stopped;
  - as a fallback, drafts that were never queued: target set, `validatedBy` null, no row for the target and stored fingerprint, and `modified` older than three days.

  Embargoed drafts are listed in a separate section, since they don't block owners yet.
- **Alerts.** Sentry reports task errors, and an alert fires when the `validation` queue grows past a threshold.

## Old files vs. new checks (accepted trade-off)

Drafts are always validated with the latest validation target, so files carried over from earlier releases are re-checked with the latest validators. A minor metadata enhancement could therefore be blocked by a check that did not exist when the file was published. This is accepted, because it means content and structure enhancements go hand-in-hand with metadata ones.

# Lifecycles

**Draft.**

1. The owner changes the draft, and it goes `PENDING`.
2. Metadata validation stores the new fingerprint, stamps `validatedRequiredVersions` with the target and sets `validatedBy = null`. The draft becomes `INVALID` with the error "a validation record … is required to publish", which the UI shows as "Content validation queued".
3. The manifest hook queues validation, or the reconciler does once every checksum exists.
4. The run completes. If the draft still has the same fingerprint, the row is stored and the draft is stamped:
   - if it has no errors, `validatedBy = true` and the draft becomes `VALID`, so it can be published;
   - if it has errors, `validatedBy = false`, and the banner and dialog list them.

   If the draft changed during the run, the row is superseded and the reconciler queues a new run.

**New validator release.**

1. Commit the next environment's lock file and deploy. The worker builds both environments, and the reconciler validates drafts with both, target first. Rows for the next code don't affect anything.
2. Once drafts have rows for the next code, change `DJANGO_DANDI_VALIDATION_TARGET`.
3. Set drafts to `PENDING`, with a management command, so they re-stamp.
4. Delete the old lock file.

Drafts already have rows for the new target, so publication is not interrupted. Published versions keep their frozen validator versions.

# Rollout

1. **dandi-schema:** add `ValidatorType`, the two fields and the publication rule, then bump the version and release.
2. **datalad-fuse:** release with the remfile backend.
3. **dandi-cli:** release with the streaming stack, the `INTERNAL` classification and the NWB Inspector fix.
4. **dandi-archive:** upgrade dandischema and run `migrate_version_metadata --all`. Ship the table, fingerprint column and backfill, task, reconciler, environments, process type, stamping, publish-time copy, `/info/` fields, banner and daily check, with the worker disabled and the target unset.
5. **dandi-infrastructure:** add the worker formation, staging first.
6. **Pilot** on a small, a BIDS and a large Dandiset. Measure seconds per file, peak memory, bytes read, cold environment build time, fingerprint hashing time on the largest draft, the cost of a run after a restart empties the cache, and how long the largest Dandiset takes compared with Heroku's daily dyno restart. Then choose the dyno size and count.
7. **Shadow mode:** enable the worker with the target unset. Results and the banner appear, but publication is not gated.
8. **Sweep** every draft and every published version. Either scale the worker up temporarily, or run the same lock file as a container near the bucket and import the results with a management command; estimate the cost first.
   - **Capacity:** `files × seconds per file ÷ processes`. For example, 500k files at 30 seconds each is about 170 process-days, or about 11 days with 16 processes.
   - **Regions:** Heroku's US region runs in AWS us-east-1, while the bucket is in us-east-2.
   - Versions published before this feature get rows only, which drive the banner.
9. **Review:** when the majority of records are available, review them for accuracy and summarize potential effects and performance.
10. **Set the target**, then set drafts to `PENDING` so they are stamped. The existing `revalidate --versions` management command cannot do this as is: `validate_version_metadata` returns early unless a version is `PENDING`, so the command must first set them `PENDING`.

# Alternatives to consider

- **A dedicated publish check in the archive instead of a schema rule.** This would need changes to `Version.publishable` and `_lock_dandiset_for_publishing`, a new exception, and frontend gating, all of which the schema rule reuses. The schema rule also makes the requirement visible to anyone validating DANDI metadata.
- **An external trusted runner (the previous design).** A runner on separate compute would validate the `dandisets/` DataLad clones and push summaries through a staff-only endpoint. It was not chosen because the backup lag adds publication latency, it cannot read embargoed content, and it needs separate record storage and a write endpoint. Running the same lock file as a container outside Heroku remains an option for the initial sweep.
- **Store full records in the archive database.** They are large, and it would tie the archive to dandi-cli's record model, which rejects unknown enum values.
- **A richer provenance object**, e.g. a `ValidationActivity(Activity)` with `Software` entries in `wasAssociatedWith`, mirroring `publishedBy: PublishActivity`. It is more expressive, but the map and boolean are simpler to look up and to enforce in `check_publication_status`.

# Open questions

1. **Isolation level.** The subprocess drops credentials, but runs on a dyno whose environment holds them. Full isolation would need a separate Heroku app without database or bucket-write credentials, which would bring back a narrow write endpoint with its own token. Is the subprocess enough?
2. **Worker size and sweep budget.** Which dyno size and count, and where should the initial sweep run (Heroku scaled up, or a container near the bucket)? To be decided from the pilot.
3. **Retry thresholds.** How many retries, and how much backoff, before a run is marked failed?
4. **Zarr.** Every asset should be NWB or BIDS, and either can be stored as Zarr. Zarr-backed assets are reported as "not checked" for now. Should validation include them?
