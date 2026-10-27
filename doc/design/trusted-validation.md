# Trusted File and Dataset Validation

Authors: Cody Baker

Status: proposal

## Overview

Today the archive only validates *metadata*:

- Each Asset's metadata is checked against the `PublishedAsset` schema.
- The draft Version's metadata is checked against the `PublishedDandiset` schema.

Neither the archive backend nor any external service runs the validators that check the *contents* of files nor the *layout* of datasets: NWB Inspector, PyNWB validation, BIDS validator, or even the ad-hoc DANDI layout enforced by CLI command `dandi validate`. As a result, Dandisets with invalid NWB files or BIDS/DANDI layouts can be published (e.g. [#2412](https://github.com/dandi/dandi-archive/issues/2412)).

This document proposes:

1. Run `dandi validate` from a trusted, internal compute source over every Dandiset version, more than 2 PB in total. This uses the streaming support being developed in dandi-cli ([dandi/dandi-cli#1956](https://github.com/dandi/dandi-cli/pull/1956)).
2. Store the resulting validation records outside the archive, served from the GitHub CDN.
3. Record in each Version's metadata the exact validator versions its records must come from. Also record whether a record exists for those versions that has no errors.
4. Prevent publication when that is not the case, and show a banner with errors *and* warnings to everyone viewing the Dandiset. This addresses [#1486](https://github.com/dandi/dandi-archive/issues/1486).

The design keeps changes small in every repository:

| Repository | Change |
|---|---|
| dandi-schema | Two read-only `Dandiset` fields, one publication rule, one schema version bump |
| dandi-archive | One table, one endpoint, a few lines in draft validation, `/info/` fields, a banner |
| dandi-infrastructure | One config var |
| dandi-cli | Bug fixes so records carry correct validator versions |

## Current state

These are the parts of the archive this design builds on.

- **Version status and publishing.**
  - `Version.status` reflects *Dandiset metadata* validation only.
  - `Version.publishable` requires `status == VALID` and every asset `VALID`.
  - `_lock_dandiset_for_publishing` refuses to publish otherwise.
- **Draft validation is publish-time validation.** `validate_version_metadata` (`dandiapi/api/services/metadata/`):
  - builds the would-be published metadata with `_build_publishable_version_from_draft`, which injects `datePublished` and `publishedBy`;
  - validates it against `PublishedDandiset`;
  - stores the outcome in `Version.status` / `Version.validation_errors`.

  Any rule dandischema enforces on *published* Dandisets therefore already marks the draft `INVALID`. That blocks publishing, and the UI shows the error in its existing validation dialog.
- **When validation runs.** Every change to a draft (adding or removing assets, editing metadata, unembargoing, Zarr ingestion) sets the draft to `PENDING`. A beat job (`validate_draft_version_metadata`, every `DANDI_VALIDATION_JOB_INTERVAL` seconds) then re-validates it.
- **Publishing copies the draft's metadata.** `_build_publishable_version_from_draft` deep-copies the draft's metadata into the new published Version. Published metadata is immutable.
- **Server-computed fields** such as `assetsSummary` are removed from user-supplied metadata by `Version.strip_metadata`.
- **Assets are shared.** Asset rows are shared between draft and published Versions. Published assets are never re-validated (`AssetHasBeenPublishedError`).

## Goals

- A Dandiset version cannot be published unless a trusted validation record for its current content contains no errors.
- The record must come from an exact, known set of validator versions:
  - **Draft:** the latest set the archive is configured for.
  - **Published version:** frozen at publication, so later validator releases never make it invalid.
- Errors and warnings are shown in a banner on the Dandiset landing page. Warnings do not block publication but reflect overall quality.
- Full records stay out of the archive database; the archive stores only small summaries.

## Non-goals

- Running validators inside the archive. All file access stays on the trusted compute side.
- Changing published metadata of already-published versions. Results for those versions only drive the banner.
- Per-asset validation status driven by these records. See [Alternatives considered](#alternatives-considered).

## Terminology

- **Validator versions:** the map of validator name to exact version used to produce a record. For example:

  ```json
  {"dandi": "0.75.0", "nwbinspector": "0.6.5", "bids-validator-deno": "2.1.0"}
  ```

  Keys are the `Validator` values that dandi-cli already writes into each record's `origin.validator`, so records can be checked against the map directly.
- **Canonical string:** the single string form of a validator-versions map. It is used in record filenames, in the API path, and in the archive's setting.
  - **Form:** for each entry write `name-version`, sort by name, and join with `_`. Example: `bids-validator-deno-2.1.0_dandi-0.75.0_nwbinspector-0.6.5`.
  - **Parsing:** split on `_`, then split each part on its last `-`.
  - **Why this is unambiguous:** normalized distribution names contain no `_`, and normalized PEP 440 versions contain neither `-` nor `_`.
- **Validation target:** the validator-versions map that drafts currently must be validated with. It is an archive setting.
- **Content fingerprint:** a hash identifying exactly which files were validated (see [Content fingerprint](#content-fingerprint)).

## Proposed solution

### dandi-schema

Add two read-only fields to `Dandiset`. Map-valued fields keyed by an enum already exist (`BareAsset.digest: Dict[DigestType, str]`).

```python
class ValidatorType(Enum):
    """Validators whose versions identify a Dandiset validation record"""

    dandi = "dandi"
    nwbinspector = "nwbinspector"
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

Extend `Dandiset.check_publication_status`, inside the branch for published Dandisets (the one where `datePublished` is set):

```python
if self.validatedRequiredVersions is not None and self.validatedBy is not True:
    err(
        "validatedBy",
        "a validation record without errors, produced with validatedRequiredVersions, "
        "is required to publish",
    )
```

The rule only applies when `validatedRequiredVersions` is set. That means:

- Already-published metadata, which lacks the field, stays valid.
- Archive instances that don't enable the feature are unaffected.

Housekeeping:

- Bump `DANDI_SCHEMA_VERSION`.
- Add the previous version to `ALLOWED_INPUT_SCHEMAS`.
- Add `("<new version>", ["validatedRequiredVersions", "validatedBy"])` to `SIMPLE_DOWNGRADES` in `migrate()`.

### dandi-archive

#### Setting

Add `DANDI_VALIDATION_TARGET`, read from `DJANGO_DANDI_VALIDATION_TARGET`. It holds the canonical string of the validation target. When unset, the feature is off: no fields are stamped and publication is not gated. That makes rollout and other instances (sandbox, vendored deployments) safe by default.

Expose it as `validation_target` on `/api/info/`, so the validation runner and clients can discover it.

#### Storage

Records are not stored in the archive. Each record gets one summary row:

```python
class VersionValidationSummary(TimeStampedModel):
    version = models.ForeignKey(
        Version, related_name='validation_summaries', on_delete=models.CASCADE
    )
    validators = models.CharField(max_length=255)  # canonical string
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

A Version can hold rows for several validator-versions maps. Only the row matching its `validatedRequiredVersions` affects publication. The other rows are informational, and they let the next validation target be pre-computed before it is switched on.

Writing a row never touches `Version.modified` or `Version.metadata` directly.

#### Endpoints

| Method | Path | Permission |
|---|---|---|
| `GET` | `/api/dandisets/{id}/versions/{version}/validation_summary/` | public (list of rows) |
| `GET` | `/api/dandisets/{id}/versions/{version}/validation_summary/{validation_versions}/` | public |
| `PUT` | `/api/dandisets/{id}/versions/{version}/validation_summary/{validation_versions}/` | `IsAdminUser` |

`{validation_versions}` is a canonical string. The trusted runner authenticates with a staff user's existing API token, so no new authentication mechanism is needed.

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
  "report_url": "https://cdn.jsdelivr.net/gh/<org>/<repo>@<commit-sha>/000029/draft/bids-validator-deno-2.1.0_dandi-0.75.0_nwbinspector-0.6.5.jsonl"
}
```

On `PUT` the archive:

1. **Validates the request.** The path must parse as a canonical string, and the body must match the schema above.
2. **Computes `success`** as `counts.CRITICAL + counts.ERROR == 0`. Which severities block publication is therefore an archive policy, not a runner decision.
3. **Upserts the row** for `(version, validators)`. Re-running the same validator versions, for example after a runner bug fix, overwrites the row.
4. **Re-pends a draft.** If the version is the draft and its status is `VALID` or `INVALID`, the archive sets it to `PENDING`. The existing beat job then recomputes `validatedBy` and the draft's status within one job interval. A draft that is `Publishing` or `Published` is left alone.

`report_url` should point at an immutable location, such as a jsDelivr URL pinned to a commit SHA rather than a branch. The archive stores it but never fetches it.

#### Content fingerprint

A record must describe the draft's *current* content. Without that check, a record produced from a stale DataLad clone could approve newer, unvalidated content.

The fingerprint is the SHA-256 of the sorted list of `(path, digest)` pairs for the version's assets:

- `digest` is the blob's DANDI etag (`AssetBlob.etag`) or the Zarr checksum (`ZarrArchive.checksum`).
- The runner computes it from the files it validated.
- The archive computes it from the Version's current assets.

Dandiset-level metadata is excluded, because the archive already validates it independently.

#### Stamping and lookup during draft validation

`validate_version_metadata` already runs after every draft change and holds a row lock on the Version. When `DANDI_VALIDATION_TARGET` is set, it would first merge two fields into the draft's metadata, then validate as today:

```python
def _validation_fields(version: Version) -> dict:
    target = settings.DANDI_VALIDATION_TARGET  # parsed map, or None
    if target is None:
        return {}
    row = version.validation_summaries.filter(validators=canonical(target)).first()
    if row is None or row.content_fingerprint != content_fingerprint(version):
        passed = None  # no record for this content yet
    else:
        passed = row.success
    return {'validatedRequiredVersions': target, 'validatedBy': passed}
```

It then persists the merged metadata in the same `update()` that stores `status` and `validation_errors`.

Because the validation copy contains `datePublished`, the new dandischema rule turns `validatedBy is not True` into a normal validation error on the field `validatedBy`. The draft becomes `INVALID`, and the existing publish gating and UI handle the rest. **No change to the publish service is needed.**

`Version.strip_metadata` adds `validatedRequiredVersions` and `validatedBy` to its computed fields, so owners cannot set them through the metadata editor or the API.

The concurrent `aggregate_assets_summary` task already uses optimistic concurrency on `metadata`. If validation changed the metadata underneath it, it retries.

#### Publication

`_build_publishable_version_from_draft` already copies the draft's metadata, so the published Version inherits `validatedRequiredVersions` and `validatedBy: true`. Since published metadata is immutable, the published version stays tied to those validator versions permanently. New validator releases cannot invalidate it.

`_publish_dandiset`'s final `validate(..., 'PublishedDandiset')` enforces the rule a second time.

#### Read API

- `VersionDetailSerializer` (the `/versions/{version}/info/` payload already loaded by the landing page) gains `validation_summary`. This is the row matching the Version's `validatedRequiredVersions`, or for versions without that field, the most recent row. The field is `null` if there is none.
- It also includes a `stale` flag for drafts, set when the row's fingerprint differs from the current content.
- The raw metadata endpoint `GET /api/dandisets/{id}/versions/{version}/` exposes `validatedRequiredVersions` and `validatedBy` directly. That is how a runner learns which validator versions a published version requires.

#### Frontend

- **Banner** at the top of `DandisetMain.vue`, visible to everyone:
  - error styling if errors exist, warning styling if only warnings exist, nothing or a small "validated" chip otherwise;
  - text naming the validators and their versions;
  - "results predate the latest changes" when `stale`, and "validation pending" when `validation_summary` is `null` but the version has `validatedRequiredVersions`.
- **Details:** opens `ValidationErrorDialog.vue` with a new tab built from `top_issues`, plus a link to the full JSONL at `report_url`. Each issue maps to the dialog's existing `{field, message, path}` shape, so grouping by path works unchanged.
- **Publish button:** no new logic. The schema error on `validatedBy` already disables it via `version_validation_errors`. Add an entry for `validatedBy` to `VALIDATION_ICONS` and a clearer message for it.

### dandi-infrastructure

Add one line under `# DANDI-specific variables` in `terraform/api.tf`, and in `staging.tf` if staging should gate too:

```hcl
DJANGO_DANDI_VALIDATION_TARGET = "bids-validator-deno-2.1.0_dandi-0.75.0_nwbinspector-0.6.5"
```

Bumping the target is then a reviewed infrastructure change.

### dandi-cli

These need to land before the full sweep:

- **NWB Inspector version is always empty.** Every NWB Inspector record currently reports `validator_version: ""`, because the cache in `_get_nwb_inspector_version` (`dandi/files/bases.py`) starts as `""` and is checked with `is not None`. Without the fix, records cannot be checked against `validatedRequiredVersions`.
- **Absolute paths.** Records contain absolute local paths. They must be relative to the Dandiset root to map to asset paths and to avoid exposing the compute layout. This can be done by the runner first, and by a CLI option later.
- **Unstable IDs and wrong `dandiset_path`.**
  - pynwb result IDs embed the error message (`pynwb.<message>`), so the runner should group them under a fixed ID when building `top_issues`.
  - NWB Inspector results set `dandiset_path` to the file's parent directory instead of the Dandiset root.

### Validation runner (trusted compute)

The runner is outside these repositories; this is its contract with the archive.

1. **Choose the validator versions.**
   - For a published Version with `validatedRequiredVersions` in its metadata, run exactly those versions against that release's tag in the `dandisets/` DataLad clone.
   - For drafts, use `/api/info/`'s `validation_target`.
   - Any other validator versions may be run and uploaded too, for example to pre-compute the next target.
2. **Validate**, with `--min-severity INFO -f json_lines`, so that warnings and hints are recorded.
3. **Upload and summarize.**
   - Relativize paths.
   - Push the JSONL to the results repository under a filename built from the canonical string.
   - Compute the counts, `top_issues`, and the content fingerprint.
4. **`PUT`** the summary to `validation_summary/{canonical}/`.
5. **Prioritize** drafts whose `validatedBy` is `null` or whose `validation_summary` is `stale`. These are the drafts whose owners are waiting to publish.

## Lifecycles

**Draft, normal path.**

1. The owner uploads.
2. The draft goes `PENDING`.
3. Validation stamps `validatedRequiredVersions = target` and `validatedBy = null`. The draft becomes `INVALID`, with the error "a validation record … is required to publish".
4. The runner validates the new content and `PUT`s its summary; the draft goes back to `PENDING`.
5. Validation finds the matching row:
   - if it has no errors, `validatedBy = true` and the draft becomes `VALID`, so it can be published;
   - if it has errors, `validatedBy = false`, and the banner and dialog list them.

**Publication.** The published Version's metadata contains `validatedRequiredVersions` and `validatedBy: true`, permanently.

**New validator release.**

1. Run the sweep with the new validator versions. Its rows are stored without affecting anything.
2. Change `DJANGO_DANDI_VALIDATION_TARGET`.
3. Set drafts to `PENDING`, with a management command, so they re-stamp.

Drafts already have rows for the new target, so publication is not interrupted. Published versions keep their frozen validator versions.

**Already-published versions (before this feature).** They have no `validatedRequiredVersions`. Sweep results are stored as rows and drive the banner only.

## Rollout

1. dandi-cli: fix the NWB Inspector version and release.
2. dandi-schema: add `ValidatorType`, the two fields, and the publication rule; bump and release.
3. dandi-archive: upgrade dandischema, then ship the table, endpoints, stamping, `/info/` fields, and banner. The feature stays off while the setting is unset.
4. Run the full sweep and upload summaries for every draft and published version.
5. dandi-infrastructure: set `DJANGO_DANDI_VALIDATION_TARGET`.
6. Set all drafts to `PENDING` so they are stamped and evaluated.

   The existing `revalidate --versions` management command cannot be used as is: `validate_version_metadata` returns early unless a version is `PENDING`, so it should first set them `PENDING`.

## Alternatives considered

- **Fail the existing per-asset status.**
  - Asset rows are shared between draft and published Versions, so one status can't reflect different validator versions per Version.
  - Published assets are never re-validated, so an unchanged file carried into a new draft could never block it.
  - BIDS and other dataset-level results have no single asset.
  - Mapping millions of records onto asset rows on every sweep is expensive.
- **Store full records in the archive database.** Large, schema-coupled to dandi-cli's record model (which rejects unknown enum values), and unnecessary: the CDN already serves them.
- **The archive pulls summaries from the CDN instead of the runner pushing them.**
  - It needs a periodic re-check of every draft lacking a passing record, plus a CDN base-URL setting, and it suffers CDN cache lag.
  - With a push, the runner signals exactly when a result exists.
  - Pulling can be added later using the same table.
- **A richer provenance object** (e.g. a `ValidationActivity(Activity)` with `Software` entries in `wasAssociatedWith`, mirroring `publishedBy: PublishActivity`). More expressive, but the map and boolean are simpler to look up and to enforce in `check_publication_status`.
- **A dedicated publish check in the archive instead of a schema rule.** It would require changes to `Version.publishable`, `_lock_dandiset_for_publishing`, a new exception, and frontend gating. The schema rule reuses all of those, and also makes the requirement visible to anyone validating DANDI metadata.

## Open questions

1. **Field names.** In dandischema, `*By` fields hold an agent or activity (`publishedBy`, `wasGeneratedBy`, `wasAttributedTo`), so a boolean `validatedBy` may surprise readers. Alternatives include `validationPassed` for the boolean and `validatorVersions` for the map. The names must be settled before the schema is released.
2. **Map keys.** Plain distribution names, matching dandi-cli's `Validator` values, or namespaced values like `DigestType`'s `dandi:sha2-256`?
3. **Should other versions be in the map?** pynwb, hdmf and dandischema also affect results. Should they be part of `validatedRequiredVersions`, or is a lock file per validator-versions map on the runner side enough?
4. **Blocking severities.** The proposal blocks on `ERROR` and `CRITICAL` only. NWB Inspector `CRITICAL` maps to `ERROR`, best-practice violations to `WARNING`, and suggestions to `HINT`; BIDS validator errors map to `ERROR` and its warnings to `HINT`.
5. **Admin override.** The schema rule blocks superusers too. Is an override needed, for example an admin-only flag on the `PUT` that forces `success`?
6. **Fingerprint source.** Confirm that the `dandisets/` DataLad clones expose each file's DANDI etag or Zarr checksum, so the runner can compute the fingerprint from what it actually validated.
7. **Publication latency.** After any change, owners wait for the DataLad backup plus a runner pass before they can publish. That also applies after an embargo is lifted, once content becomes publicly readable. What turnaround should the runner guarantee?
8. **Old files vs. new checks.** Files from earlier releases are re-checked with the latest validators. A metadata-only fix could be blocked by a check that did not exist when the file was published.
9. **`modified` bumps.** Re-pending a draft after a `PUT` makes `validate_version_metadata` bump `Version.modified`, which moves the "Last update" date for a change that is not a content change. Consider not bumping `modified` when only the validation fields change (see also [#2950](https://github.com/dandi/dandi-archive/pull/2950)).
10. **CDN limits.** GitHub rejects files over 100 MB, and jsDelivr has its own per-file limits. The largest Dandisets may need compressed or sharded JSONL.
11. **Listing indicators.** [#741](https://github.com/dandi/dandi-archive/issues/741): a compact error/warning indicator in the Dandiset list, derived from the same rows.
