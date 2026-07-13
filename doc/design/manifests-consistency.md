# Manifest consistency on S3

Author: Yaroslav O. Halchenko (with Claude Code assistance)

Tracking issue: [dandi/dandi-archive#2759](https://github.com/dandi/dandi-archive/issues/2759)

## Overview

For every Dandiset version the archive writes five manifest files under
`dandisets/<dandiset_id>/<version>/` on S3:

- `dandiset.jsonld`
- `assets.jsonld`
- `dandiset.yaml`
- `assets.yaml`
- `collection.jsonld`

These are intended to be a faithful, dereferenceable, on-S3 representation of
the metadata that the Django archive holds for that version. Several
deployments and downstream consumers (e.g. `linkml`-ification efforts, mirrors,
the `dandiset-manifests` clone at `drogon`) treat the S3 copy as authoritative.

Issue #2759 documented two failure modes:

1. **Missing or placeholder DOIs** in published `dandiset.jsonld` files — for
   most recently published versions the `doi` field is `null` or, in a small
   number of older publications, the publish-time placeholder
   `10.80507/dandi.123456/0.123456.1234`.
2. **Drift between S3 and the database** — older manifests can disagree with
   the current DB state in fields that are recomputed (`assetsSummary`,
   `citation`, `manifestLocation`, etc.) or were corrected post-publish (e.g.
   the affiliation-corruption migration handled by
   `correct_metadata`).

A reproducer script attached to the issue compares
`https://dandiarchive.s3.amazonaws.com/dandisets/<id>/<ver>/dandiset.jsonld`
against `https://api.dandiarchive.org/api/dandisets/<id>/versions/<ver>/`.

## Root cause analysis

### Missing DOIs — race in `_publish_dandiset`

In `dandiapi/api/services/publish/__init__.py` the publish path schedules two
*independent* `transaction.on_commit` callbacks:

```python
transaction.on_commit(lambda: write_manifest_files.delay(new_version.id))

def _create_doi(version_id: int):
    version = Version.objects.get(id=version_id)
    version.doi = doi.create_doi(version)
    version.save()

transaction.on_commit(lambda: _create_doi(new_version.id))
```

Sequence at runtime, after the publish transaction commits:

1. `write_manifest_files.delay(new_version.id)` is **enqueued** to the celery
   broker (returns immediately).
2. `_create_doi(new_version.id)` runs **synchronously** in the publish task,
   issuing an HTTP request to DataCite and then `version.save()`-ing the
   result. `Version.save()` calls `_populate_metadata`, which copies
   `self.doi` into `metadata['doi']` and rebuilds `citation`.

There is no ordering between (1) and (2). A celery worker that picks up the
manifest task can read `Version` from the DB before the DOI commit lands. The
result is a published `dandiset.jsonld` written from a version whose
`metadata` does not yet contain `doi`, and consequently has the
non-DOI form of `citation`. **Nothing re-runs `write_manifest_files` after
`_create_doi` saves the DOI**, so the stale manifest persists indefinitely.

Notes:

- The "dummy DOI" injected at lines ~187 of `_publish_dandiset` is set on the
  in-memory `new_version.metadata` purely to make the `validate(...)` call
  pass. The publish path does not `save()` the new version after that
  injection (the last preceding `save()` had `self.doi=None`, so
  `_populate_metadata` did not propagate the dummy into the persisted
  metadata), so it does not normally end up in the manifest. The handful
  of older manifests that do contain it are an artifact of an earlier
  publish code path that *did* persist the placeholder.
- If `_create_doi` itself fails (DataCite outage, network), `version.doi`
  stays `NULL` in the DB and is never retried; the manifest is then
  permanently DOI-less even from the DB's point of view.

### Drift on older manifests

Independently of DOIs, any change to `Version.metadata` that does not
trigger `write_manifest_files` (schema migrations, `correct_metadata`,
`migrate_published_version_metadata`, manual fixups, recomputations of
`assetsSummary`) will leave the on-S3 manifest stale. Issue #2759 shows
000004's draft as an example: the S3 `assetsSummary` is `{numberOfBytes:0,
numberOfFiles:0}` while the API has the populated summary.

## Plan

The work splits into three deliverables. Only #1 is in scope for the
present change.

### 1. New management command: `sync_manifest_files`

Path: `dandiapi/api/management/commands/sync_manifest_files.py`

Purpose: reconcile S3 manifests against the database. For each selected
Version, parse the on-S3 `dandiset.jsonld` and/or `assets.jsonld`, compare
to what the current `Version.metadata` / `Version.assets` would render, and
if they differ (or if the S3 object is missing), invoke
`write_manifest_files(version.id)` to rewrite all five manifest files.
Optionally re-mint DOIs for published versions whose `Version.doi` is `NULL`
or matches the placeholder.

Surface (current):

```
./manage.py sync_manifest_files [DANDISET_ID …] [-a/--all]
    [--version draft|published|all]      # default: all
    [--specific-version VER]              # overrides --version
    [--targets dandiset|assets|both]      # default: dandiset
    [--dry-run / --check]
    [--sync / --async]                    # default: --async
    [--fix-doi / --no-fix-doi]            # default: --fix-doi
    [--show-diff]
```

Defaults follow operational ergonomics for the live deployment:

- `--targets=dandiset` is the cheap default; comparing every
  `assets.jsonld` for every version is expensive (large dandisets).
- `--async` enqueues regenerations via celery, so a single invocation can
  fan out across workers.
- `--fix-doi` is on so that a single sweep restores both DOIs and manifests
  "once and for all"; opt-out with `--no-fix-doi` for a manifest-only run.

Comparison is **semantic**: both sides are parsed as JSON and compared as
Python objects, so whitespace/key-ordering differences do not produce false
mismatches. With `--show-diff` a `difflib.unified_diff` of the
sort-keyed pretty-printed forms is emitted.

DOI re-minting calls `dandiapi.api.doi.create_doi(version)` synchronously
(so failures surface in the operator's terminal). When DataCite is not
configured the HTTP call itself is skipped, but `_generate_doi_data` still
runs full `PublishedDandiset` schema validation via
`dandischema.datacite.to_datacite`; the function only returns the
deterministically computed DOI when validation succeeds. If validation
fails the in-memory `version.metadata['doi']` is rolled back via
`version.refresh_from_db()` so the immediately following S3 comparison
is not corrupted.

### 2. Fix the publish race

Replace the two parallel `on_commit` callbacks in `_publish_dandiset` with
a single chained one so manifest writing is enqueued **after** the DOI is
committed. Failures at either substep are logged distinctly (so it's clear
whether the DOI was minted-but-not-saved or never minted at all) and do
not abort the manifest write — even a DOI-less published version is better
represented by a manifest on S3 than by nothing. `sync_manifest_files
--fix-doi` later reconciles whatever was missed.

```python
def _create_doi_and_write_manifests(version_id: int):
    version = Version.objects.get(id=version_id)
    new_doi: str | None = None
    try:
        new_doi = doi.create_doi(version)
    except Exception:
        logger.exception('Failed to mint DOI for version %s', version_id)
    if new_doi is not None:
        try:
            version.doi = new_doi
            version.save()
        except Exception:
            logger.exception(
                'Minted DOI %s but failed to persist it on version %s',
                new_doi, version_id,
            )
    write_manifest_files.delay(version_id)

transaction.on_commit(lambda: _create_doi_and_write_manifests(new_version.id))
```

Future hardening (not included here): turn `_create_doi_and_write_manifests`
into a real celery `shared_task` with `autoretry_for=(requests.RequestException,)`
so transient DataCite failures auto-recover rather than relying on an
operator-driven `sync_manifest_files --fix-doi` sweep.

### 3. One-off operational sweep

After #1 lands and #2 is deployed, run, in order:

```
./manage.py sync_manifest_files --all --version published --dry-run --show-diff
./manage.py sync_manifest_files --all --version published
./manage.py sync_manifest_files --all --version draft --dry-run
./manage.py sync_manifest_files --all --version draft
```

Optionally with `--targets=both` if drift in `assets.jsonld` is suspected
beyond the `dandiset.jsonld` audit.

## Testing plan

The repository already has the test infrastructure needed for this work;
no new harness is required.

### What is already in place

- **MinIO is the test storage backend.**
  `dandiapi/settings/testing.py` wires `STORAGES['default']` to
  `dandiapi.storage.MinioDandiS3Storage` pointed at
  `DJANGO_MINIO_STORAGE_URL`. Tests that touch `default_storage` exercise a
  real MinIO instance (the `minio` service in `docker-compose.yml`). This
  *is* the integration harness.
- **Eager celery.** `CELERY_TASK_ALWAYS_EAGER = True` and
  `CELERY_TASK_EAGER_PROPAGATES = True` mean
  `write_manifest_files.delay(...)` runs inline in tests, so both `--sync`
  and `--async` exercise the same code path.
- **DOI minting skips the network in tests.** `doi.create_doi` skips the
  HTTP call when any `DANDI_DOI_*` setting is `None` (which is the case
  under test settings). It is **not** pure compute, though: it still runs
  `to_datacite()`, which performs full `PublishedDandiset` pydantic
  validation on the version metadata, and faker-generated factory
  metadata does not satisfy that schema. DOI-fix tests therefore
  monkeypatch `doi.create_doi` directly rather than relying on the
  no-HTTP-call shortcut to short-circuit it (see `_install_fake_create_doi`
  in `test_sync_manifest_files.py`).
- **djclick command invocation.** Existing tests
  (`test_create_dev_dandiset.py`, `test_correct_metadata.py`) call the
  `@click.command()` function directly with argv-style positional args;
  djclick's `CommandAdapter.__call__` dispatches via `execute` with
  `standalone_mode=False`, so there is no `SystemExit` and no
  `CliRunner.invoke` boilerplate.
- **Factories.** `DraftVersionFactory`, `PublishedVersionFactory` (already
  populates `doi`), `DraftAssetFactory`, `PublishedAssetFactory`. The
  parametrized `version` fixture in `dandiapi/conftest.py` covers
  draft/published.

### Test file

`dandiapi/api/tests/test_sync_manifest_files.py`, marked `@pytest.mark.django_db`.

### Coverage matrix

| #   | Scenario                                              | Setup → Action → Assertion                                                                                                                                                                |
| --- | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| U1  | `_is_dummy_doi` truth table                           | parametrized real DOI / placeholder / None                                                                                                                                                |
| U2  | `_diff` shape                                         | unequal dicts → non-empty unified diff with expected headers                                                                                                                              |
| A1  | Happy path: nothing to do                             | seed draft + manifests → run `--all --dry-run` → S3 unchanged, summary 0 mismatches                                                                                                       |
| A2  | Drafted out-of-sync `dandiset.jsonld`                 | seed → mutate `version.metadata` and save → run `--all` → S3 `dandiset.jsonld` parsed equals `version.metadata`                                                                           |
| A3  | `--dry-run` does not write                            | as A2 with `--dry-run` → S3 still has the old content                                                                                                                                     |
| A4  | Missing S3 object treated as mismatch                 | seed → `default_storage.delete(...)` → run → file recreated                                                                                                                                |
| A5  | `--targets=assets`                                    | seed published version → mutate one asset's metadata → run with `--targets=assets` → S3 `assets.jsonld` matches expected list                                                              |
| A6  | `--targets=both`                                      | mutate both → run `--targets=both` → both files updated                                                                                                                                   |
| A7  | DOI remint: NULL doi on published version             | published version with `doi=None` → run with default `--fix-doi` → `version.doi` populated; S3 `dandiset.jsonld['doi']` matches; citation uses doi.org URL                                |
| A8  | DOI remint: placeholder doi                           | published version with `doi='…/123456/0.123456.1234'` → run → real doi minted, manifest updated                                                                                          |
| A9  | `--no-fix-doi` skips DOI fix                          | as A7 with `--no-fix-doi` → `version.doi` still NULL                                                                                                                                       |
| A10 | DOI remint failure is reported, not fatal             | monkeypatch `doi_module.create_doi` to raise → run with `--fix-doi` → command completes; output shows "DOI remint FAILED"; `version.doi` unchanged                                         |
| A11 | `--version=draft` filter                              | one draft + one published, both stale → run `--version=draft` → only draft regenerated                                                                                                    |
| A12 | `--version=published` filter                          | symmetric to A11                                                                                                                                                                          |
| A13 | `--specific-version=<ver>`                            | published v1 + v2 stale → only v1 regenerated                                                                                                                                              |
| A14 | Positional dandiset filter                            | two dandisets stale → run with one ID → only that one regenerated                                                                                                                         |
| A15 | Mutually-exclusive arg validation                     | `--all` + positional, or neither → `ClickException`                                                                                                                                       |
| A16 | Embargoed manifest re-tagged on regeneration          | embargoed dandiset, mutate metadata → run → `default_storage.get_tags(path)` includes `embargoed: 'true'`                                                                                  |
| A17 | `--show-diff` produces diff output                    | mutate metadata → run with `--show-diff` → captured stdout contains the unified-diff headers                                                                                              |

### Notes / caveats

- `_dandiset_jsonld_matches` runs the DB-side metadata through
  `json.loads(JSONRenderer().render(...))` (via the `_renormalize` helper)
  before comparing to `json.loads(s3_bytes)`, so a future field that
  involves DRF-specific coercion (`Decimal`, `UUID`, `datetime`) does not
  produce a one-sided mismatch.
- `default_storage.open(...).read()` returning `bytes` for S3-backed storage
  is assumed (existing `test_manifests.py` does the same).
- "Mock S3" is intentionally **not** introduced. The existing MinIO-based
  setup is more faithful and is already what CI runs.

### Running

- Local: `docker compose up -d minio postgres rabbitmq`
  then `tox -e test -- dandiapi/api/tests/test_sync_manifest_files.py`.
- CI: covered by the existing `[testenv:test]` env; no workflow changes.

## Open questions

- Should `sync_manifest_files` also reconcile `assets.yaml` /
  `dandiset.yaml` / `collection.jsonld` independently, or is regenerating
  all five from a `dandiset.jsonld` mismatch sufficient? (Current design:
  any mismatch triggers full regeneration via `write_manifest_files`,
  which rewrites all five.)
- Should DOI re-minting attempt to *recover* an existing DataCite DOI
  (e.g. via `GET` before `POST`) so it does not fail-loud on duplicate
  creation when `version.doi` is NULL but the DOI was actually minted in
  a prior partially-failed run?
- Do we want a periodic/scheduled invocation (celery beat) of a
  manifest-consistency audit, or is on-demand operator invocation
  sufficient?
