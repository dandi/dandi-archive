# Trusted File and Dataset Validation

Authors: Cody Baker

Status: proposal

## Contents

- [Overview](#overview)
- [Current state](#current-state)
- [Goals](#goals)
- [Non-goals](#non-goals)
- [Terminology](#terminology)
- [Proposed solution](#proposed-solution)
  - [dandi-schema](#dandi-schema)
  - [dandi-archive](#dandi-archive)
  - [Record storage (to be decided)](#record-storage-to-be-decided)
  - [dandi-infrastructure](#dandi-infrastructure)
  - [dandi-cli](#dandi-cli)
  - [Validation runner](#validation-runner)
  - [Publication latency (accepted trade-off)](#publication-latency-accepted-trade-off)
- [Lifecycles](#lifecycles)
- [Rollout](#rollout)
- [Alternatives to consider](#alternatives-to-consider)
- [Open questions](#open-questions)

## Overview

Today the archive only validates *metadata*: each Asset's metadata against the `PublishedAsset` schema, and the draft Version's metadata against the `PublishedDandiset` schema.

Neither the archive backend nor any external service runs the validators that check the *contents* of files nor the *layout* of datasets: NWB Inspector, PyNWB validation, BIDS validator, or even the ad-hoc DANDI layout enforced by CLI command `dandi validate`. As a result, Dandisets with invalid NWB files or BIDS/DANDI layouts can be published (e.g. [#2412](https://github.com/dandi/dandi-archive/issues/2412)).

This document proposes running `dandi validate` from a trusted, internal compute source over every Dandiset version, more than 2 PB in total. This uses the streaming support being developed in dandi-cli ([dandi/dandi-cli#1956](https://github.com/dandi/dandi-cli/pull/1956)).

- **Records and summaries:** the full records go to separate storage, still to be decided. The archive keeps only a small summary of each result.
- **Required versions:** each Version's metadata records the exact validator versions its result must come from.
- **Gating:** the archive blocks publication unless that result has no errors.

The changes in each repository are small:

| Repository | Change |
|---|---|
| dandi-schema | Two read-only `Dandiset` fields, one publication rule, one schema version bump |
| dandi-archive | One table, one endpoint, a few lines in draft validation, `/info/` fields, a banner |
| dandi-infrastructure | One config var, plus whatever record storage needs |
| dandi-cli | Bug fixes so records carry correct validator versions |

## Current state

These are the parts of the archive this design builds on.

- **Version status and publishing.** `Version.status` reflects *Dandiset metadata* validation only. `Version.publishable` requires `status == VALID` and every asset `VALID`, and `_lock_dandiset_for_publishing` refuses to publish otherwise.
- **Draft validation is publish-time validation.** `validate_version_metadata` (`dandiapi/api/services/metadata/`) does three things:
  - it builds the would-be published metadata with `_build_publishable_version_from_draft`, which injects `datePublished` and `publishedBy`;
  - it validates that metadata against `PublishedDandiset`;
  - it stores the outcome in `Version.status` / `Version.validation_errors`.

  Any rule dandischema enforces on *published* Dandisets therefore already marks the draft `INVALID`. That blocks re-publishing at a later time, and the UI shows the error in its existing validation dialog.
- **When validation runs.** Every change to a draft (adding or removing assets, editing metadata, unembargoing, Zarr ingestion) sets the draft to `PENDING`. A beat job (`validate_draft_version_metadata`, every `DANDI_VALIDATION_JOB_INTERVAL` seconds) then re-validates it.
- **Publishing copies the draft's metadata.** `_build_publishable_version_from_draft` deep-copies the draft's metadata into the new published Version. Published metadata is immutable.
- **Server-computed fields** such as `assetsSummary` are removed from user-supplied metadata by `Version.strip_metadata`.

## Goals

- A Dandiset version cannot be published unless a trusted validation record for its current content contains no errors.
- The record must come from an exact, known set of validator versions:
  - **Drafts:** the latest set the archive is configured for.
  - **Published versions:** the set frozen at publication, so later validator releases never make them invalid.
- Errors and warnings are shown to everyone in a banner on the Dandiset landing page ([#1486](https://github.com/dandi/dandi-archive/issues/1486)). Warnings do not block publication but reflect overall quality.

## Non-goals

- Running validators inside the archive, or storing full records in its database.
- Changing the metadata of versions published before this feature. Their results only drive the banner.
- Per-asset validation status driven by these records.

## Terminology

- **Validator versions:** the map from each package that affects validation results to the exact version used to produce a record. Keys are plain distribution names, and all six are always present:

  ```json
  {"dandi": "0.75.0", "dandischema": "0.12.0", "nwbinspector": "0.7.1", "pynwb": "3.1.0", "hdmf": "4.1.0", "bids-validator-deno": "2.1.0"}
  ```

  - **Checkable against records:** every key except `hdmf` is a `Validator` value that dandi-cli writes into each record's `origin`, so those versions can be checked against each record's `origin.validator_version`.
  - **hdmf:** the runner reports its version from its own environment.
- **Version code:** a short, readable string form of a validator-versions map. It is used in the API path, in the archive's setting, and is suggested for record file names.
  - **Form:** each package's short code (see `VALIDATOR_CODES` under [dandi-schema](#dandi-schema)) followed directly by its version, in the code table's order, joined with `_`. For the map above: `cli0.75.0_schema0.12.0_nwbi0.7.1_pynwb3.1.0_hdmf4.1.0_bids2.1.0`.
  - **Parsing:** split on `_`, then split each part where its leading letters end.
  - **Why this is unambiguous:** codes contain only letters, and normalized PEP 440 versions start with a digit and contain no `_`.
- **Validation target:** the validator versions drafts must currently be validated with (see [Setting](#setting)).

## Proposed solution

### dandi-schema

Add two read-only fields to `Dandiset`. Map-valued fields keyed by an enum already exist (`BareAsset.digest: Dict[DigestType, str]`).

```python
class ValidatorType(Enum):
    """Packages whose versions identify a Dandiset validation record"""

    dandi = "dandi"
    dandischema = "dandischema"
    nwbinspector = "nwbinspector"
    pynwb = "pynwb"
    hdmf = "hdmf"
    bids_validator_deno = "bids-validator-deno"


#: Short code of each package in a version code, in the code's order
VALIDATOR_CODES = {
    ValidatorType.dandi: "cli",
    ValidatorType.dandischema: "schema",
    ValidatorType.nwbinspector: "nwbi",
    ValidatorType.pynwb: "pynwb",
    ValidatorType.hdmf: "hdmf",
    ValidatorType.bids_validator_deno: "bids",
}


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

The archive and the runner both depend on dandischema. So `VALIDATOR_CODES`, plus two small helpers that build and parse version codes, live next to `ValidatorType`, giving one definition for both. The constant does not change the JSON Schema.

**JSON-LD.** Plain distribution names are not JSON-LD terms. `dandi` would collide with the `dandi:` prefix in the `@context`, and the other keys would be dropped when the metadata is expanded. To keep the map intact, `generate_context` should give `validatedRequiredVersions` `"@type": "@json"`, so JSON-LD treats the whole map as a single JSON literal.

The schema change also needs some housekeeping:
- bump `DANDI_SCHEMA_VERSION` and add the previous version to `ALLOWED_INPUT_SCHEMAS`;
- add `("<new version>", ["validatedRequiredVersions", "validatedBy"])` to `SIMPLE_DOWNGRADES` in `migrate()`.

### dandi-archive

#### Setting

`DANDI_VALIDATION_TARGET`, read from `DJANGO_DANDI_VALIDATION_TARGET`, holds the validation target as a version code.

- **Unset:** the feature is off. Nothing is stamped and publication is not gated, so rollout and other instances (sandbox, vendored deployments) are safe by default.
- **Exposed** as `validation_target` on `/api/info/`.

#### Summary table

```python
class VersionValidationSummary(TimeStampedModel):
    version = models.ForeignKey(
        Version, related_name='validation_summaries', on_delete=models.CASCADE
    )
    validators = models.CharField(max_length=255)  # version code
    content_fingerprint = models.CharField(max_length=64)
    success = models.BooleanField()  # computed by the archive, see below
    summary = models.JSONField()  # counts, top issues, report URL, timestamps

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['version', 'validators'], name='unique-version-validators'
            )
        ]
```

There is one row per Version and set of validator versions. Only the row matching the Version's `validatedRequiredVersions` affects publication. The other rows are informational, and they let the next target be computed ahead of time (see [Lifecycles](#lifecycles)).

#### Endpoints

| Method | Path | Permission |
|---|---|---|
| `GET` | `/api/dandisets/{id}/versions/{version}/validation_summary/` | public (list of rows) |
| `GET` | `/api/dandisets/{id}/versions/{version}/validation_summary/{validation_versions}/` | public |
| `PUT` | `/api/dandisets/{id}/versions/{version}/validation_summary/{validation_versions}/` | `IsAdminUser` |

`{validation_versions}` is a version code. The trusted runner authenticates with a staff user's existing API token, so no new authentication mechanism is needed.

`PUT` body:

```json
{
  "content_fingerprint": "<sha256 hex>",
  "validated_at": "2026-10-13T08:00:00Z",
  "counts": {"CRITICAL": 0, "ERROR": 3, "WARNING": 41, "HINT": 120, "INFO": 7},
  "top_issues": [
    {
      "id": "NWBI.check_subject_species_exists",
      "severity": "WARNING",
      "count": 12,
      "example_paths": ["sub-01/sub-01_ses-1.nwb"]
    }
  ],
  "report_url": "https://<record-storage>/000029/draft/cli0.75.0_schema0.12.0_nwbi0.7.1_pynwb3.1.0_hdmf4.1.0_bids2.1.0.jsonl"
}
```

On `PUT` the archive:

1. **Validates the request.** The path must parse as a version code with all six packages, and the body must match the schema above.
2. **Computes `success`** as `counts.CRITICAL + counts.ERROR == 0`, so only `ERROR` and `CRITICAL` block publication. The archive, not the runner, applies this policy. dandi-cli maps validator severities onto its own as follows:
   - NWB Inspector: `CRITICAL` → `ERROR`, best-practice violations → `WARNING`, suggestions → `HINT`.
   - BIDS validator: errors → `ERROR`, warnings → `HINT`.
3. **Upserts the row** for `(version, validators)`. Re-running the same validator versions, for example after a runner bug fix, overwrites the row.
4. **Re-pends a draft.** If the version is the draft and its status is `VALID` or `INVALID`, the archive sets it to `PENDING`, so the next beat job recomputes `validatedBy`. A draft that is `Publishing` or `Published` is left alone.

#### Content fingerprint

A record must describe the draft's *current* content. Otherwise a record produced from a stale DataLad clone could approve newer, unvalidated content.

The fingerprint is the SHA-256 of the sorted list of `(path, digest)` pairs for the version's assets:

- `digest` is the blob's DANDI etag (`AssetBlob.etag`) or the Zarr checksum (`ZarrArchive.checksum`).
- The runner computes it from the files it validated.
- The archive computes it from the Version's current assets.

Dandiset-level metadata is excluded, because the archive already validates it independently.

#### Stamping during draft validation

When `DANDI_VALIDATION_TARGET` is set, `validate_version_metadata` first merges two fields into the draft's metadata, then validates as today:

```python
def _validation_fields(version: Version) -> dict:
    target = settings.DANDI_VALIDATION_TARGET  # parsed map, or None
    if target is None:
        return {}
    row = version.validation_summaries.filter(validators=version_code(target)).first()
    if row is None or row.content_fingerprint != content_fingerprint(version):
        passed = None  # no record for this content yet
    else:
        passed = row.success
    return {'validatedRequiredVersions': target, 'validatedBy': passed}
```

It persists the merged metadata in the same `update()` that stores `status` and `validation_errors`.

Draft validation is publish-time validation (see [Current state](#current-state)). So whenever `validatedBy` is not `true`, the new schema rule produces an ordinary validation error on `validatedBy`, and the draft becomes `INVALID`. The existing publish gating, validation dialog and Publish button handle the rest, and **the publish service needs no change**.

Two more details:
- `Version.strip_metadata` adds both fields to its computed fields, so owners cannot set them through the metadata editor or the API.
- The concurrent `aggregate_assets_summary` task already uses optimistic concurrency on `metadata`, so it retries if validation changed the metadata underneath it.

#### Publication

The published Version inherits both fields from the draft's metadata. Published metadata is immutable, so the published Version stays tied to those validator versions permanently. `_publish_dandiset`'s final `validate(..., 'PublishedDandiset')` enforces the rule a second time.

#### Read API

- **Version details:** `VersionDetailSerializer`, the `/versions/{version}/info/` payload the landing page already loads, gains two fields:
  - `validation_summary` is the row matching the Version's `validatedRequiredVersions`. For versions without that field, it is the most recent row, and it is `null` if there is no row.
  - For drafts, `stale` is set when that row's fingerprint differs from the current content.
- **Raw metadata:** both metadata fields also appear in the raw metadata at `GET /api/dandisets/{id}/versions/{version}/`.

#### Frontend

- **Banner** at the top of `DandisetMain.vue`:
  - error styling if errors exist, warning styling if only warnings exist, and nothing or a small "validated" chip otherwise;
  - text naming the validators and their versions;
  - "results predate the latest changes" when `stale`, and "validation pending" when `validation_summary` is `null` but the version has `validatedRequiredVersions`.
- **Details:** this opens `ValidationErrorDialog.vue` with a new tab built from `top_issues`, plus a link to the full records at `report_url`. Each issue maps to the dialog's existing `{field, message, path}` shape, so grouping by path works unchanged.
- **Validation error:** add an entry for `validatedBy` to `VALIDATION_ICONS`, with a clearer message.

### Record storage (to be decided)

Where the full JSONL records live is not decided yet. The archive needs three things from it:

- **A stable, immutable `report_url` per record set**, for example pinned to a commit or an object version. The archive stores it but never fetches it.
- **Public browser access to that URL**, with CORS, for the "full report" link.
- **Room for very large record files** from the largest Dandisets.

Candidates include:

- **A GitHub repository served through a CDN.** GitHub rejects files over 100 MB, and CDNs may cache branch URLs.
- **An S3 bucket.** It needs the bucket itself and write credentials for the runner.

### dandi-infrastructure

Add one line under `# DANDI-specific variables` in `terraform/api.tf`, and in `staging.tf` if staging should gate too:

```hcl
DJANGO_DANDI_VALIDATION_TARGET = "cli0.75.0_schema0.12.0_nwbi0.7.1_pynwb3.1.0_hdmf4.1.0_bids2.1.0"
```

Bumping the target is then a reviewed infrastructure change. Any infrastructure for record storage, such as a bucket and the runner's write credentials, would also go here.

### dandi-cli

These need to land before the full sweep:

- **NWB Inspector version is always empty.** Every NWB Inspector record currently reports `validator_version: ""`. The cache in `_get_nwb_inspector_version` (`dandi/files/bases.py`) starts as `""` and is checked with `is not None`. Without the fix, records cannot be checked against `validatedRequiredVersions`.
- **Absolute paths.** Records contain absolute local paths. They must be relative to the Dandiset root to map to asset paths and to avoid exposing the compute layout. The runner can do this first, and a CLI option can come later.
- **Unstable IDs and wrong `dandiset_path`.**
  - pynwb result IDs embed the error message (`pynwb.<message>`), so the runner should group them under a fixed ID when building `top_issues`.
  - NWB Inspector results set `dandiset_path` to the file's parent directory instead of the Dandiset root.

### Validation runner

The runner runs on trusted compute, outside these repositories. This is its contract with the archive:

1. **Choose the validator versions.**
   - For a published Version with `validatedRequiredVersions` in its metadata, run exactly those versions against that release's tag in the `dandisets/` DataLad clone.
   - For drafts, use `validation_target` from `/api/info/`.
   - Other validator versions may be run and uploaded too.
2. **Validate**, with `--min-severity INFO -f json_lines`, so that warnings and hints are recorded.
3. **Prepare the result.** Relativize paths (see [dandi-cli](#dandi-cli)) and store the JSONL in record storage. Then compute the counts, `top_issues` and the content fingerprint.
4. **`PUT`** the summary to `validation_summary/{version code}/`.
5. **Prioritize** drafts whose `validatedBy` is `null` or whose `validation_summary` is `stale`. These are the drafts whose owners are waiting to publish (see [Publication latency](#publication-latency-accepted-trade-off)).

### Publication latency (accepted trade-off)

After any change to a draft, its owner can publish only once the DataLad backup has caught up and the runner has validated the new content. The same applies after an embargo is lifted, once the content becomes publicly readable. This delay is accepted in exchange for publishing only validated content.

The archive monitors the delay so a stalled runner is noticed:

- **Daily check.** A beat task, scheduled like `send_pending_users_email`, lists open drafts that still lack a record for their current content three days after their last change. Embargoed drafts are left out, because the runner cannot read their content.

  ```python
  Version.objects.filter(
      version='draft',
      dandiset__embargo_status=DandisetEmbargoStatus.OPEN,
      metadata__validatedRequiredVersions__isnull=False,
      metadata__validatedBy=None,  # JSON null: no record for the current content
      modified__lt=timezone.now() - timedelta(days=3),
  )
  ```

  `modified` only approximates when the wait began. Every change to the draft resets it, and so does the re-validation that follows each `PUT`.
- **Notification.** If any drafts are found, the task emails `DANDI_DEV_EMAIL` with each Dandiset and how long it has waited. That setting already exists, so no infrastructure change is needed.

## Lifecycles

**Draft.**

1. The owner changes the draft, and it goes `PENDING`.
2. Validation stamps `validatedRequiredVersions` with the target and sets `validatedBy = null`. The draft becomes `INVALID`, with the error "a validation record … is required to publish".
3. The runner `PUT`s a summary for the new content, and the archive re-pends the draft.
4. Validation finds the matching row:
   - if it has no errors, `validatedBy = true` and the draft becomes `VALID`, so it can be published;
   - if it has errors, `validatedBy = false`, and the banner and dialog list them.

**New validator release.**

1. Run the sweep with the new validator versions. Its rows are stored without affecting anything.
2. Change `DJANGO_DANDI_VALIDATION_TARGET`.
3. Set drafts to `PENDING`, with a management command, so they re-stamp.

Drafts already have rows for the new target, so publication is not interrupted.

## Rollout

1. **dandi-cli:** fix the NWB Inspector version and release.
2. **dandi-schema:** add `ValidatorType`, `VALIDATOR_CODES`, the two fields and the publication rule, then bump the version and release.
3. **dandi-archive:** upgrade dandischema, then ship the table, endpoints, stamping, `/info/` fields and banner. The feature stays off while the setting is unset.
4. **Record storage:** decide on it and set it up.
5. **First target:** follow the "New validator release" steps above, with the sweep covering every draft and published version.

   The existing `revalidate --versions` management command cannot re-pend drafts as is. `validate_version_metadata` returns early unless a version is `PENDING`, so the command must first set them `PENDING`.

## Alternatives to consider

- **A dedicated publish check in the archive instead of a schema rule.** This would need changes to `Version.publishable` and `_lock_dandiset_for_publishing`, a new exception, and frontend gating, all of which the schema rule reuses. The schema rule also makes the requirement visible to anyone validating DANDI metadata.
- **Store full records in the archive database.** They are large, and it would tie the archive to dandi-cli's record model, which rejects unknown enum values.
- **The archive pulls summaries from record storage instead of the runner pushing them.**
  - Pulling needs a periodic re-check of every draft that lacks a passing record, plus a storage URL setting, and it suffers from any caching delay.
  - With a push, the runner signals exactly when a result exists.
  - Pulling can be added later using the same table.
- **A richer provenance object**, e.g. a `ValidationActivity(Activity)` with `Software` entries in `wasAssociatedWith`, mirroring `publishedBy: PublishActivity`. It is more expressive, but the map and boolean are simpler to look up and to enforce in `check_publication_status`.

## Open questions

1. **Field names.** In dandischema, `*By` fields hold an agent or activity (`publishedBy`, `wasGeneratedBy`, `wasAttributedTo`), so a boolean `validatedBy` may surprise readers. Alternatives include `validationPassed` for the boolean and `validatorVersions` for the map. The names must be settled before the schema is released.
2. **Admin override.** The schema rule blocks superusers too. Is an override needed, for example an admin-only flag on the `PUT` that forces `success`?
3. **Fingerprint source.** Confirm that the `dandisets/` DataLad clones expose each file's DANDI etag or Zarr checksum, so the runner can compute the fingerprint from what it actually validated.
4. **Old files vs. new checks.** Files from earlier releases are re-checked with the latest validators, so a minor metadata enhancement could be blocked by a check that did not exist when the file was published. The advantage is that content and structure enhancements go hand-in-hand with metadata ones.
5. **`modified` bumps.** Re-pending a draft after a `PUT` makes `validate_version_metadata` bump `Version.modified`. That moves the "Last update" date even though the content didn't change. Consider not bumping `modified` when only the validation fields change (see also [#2950](https://github.com/dandi/dandi-archive/pull/2950)).
6. **Record storage.** Where should records live? See [Record storage (to be decided)](#record-storage-to-be-decided).
7. **Listing indicators.** [#741](https://github.com/dandi/dandi-archive/issues/741) asks for a compact error/warning indicator in the Dandiset list, derived from the same rows.
