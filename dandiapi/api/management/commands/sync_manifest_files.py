"""
Management command to reconcile manifest files on S3 against the database.

For each selected Version, compare what `dandiset.jsonld` and/or `assets.jsonld`
would be generated now from `version.metadata` / `version.assets` to what's
currently stored on S3. If they differ (or if the S3 object is missing),
trigger `write_manifest_files` to rewrite all manifest files for that version.

Optionally also re-mint DOIs for published versions whose `version.doi` is
NULL or equals the placeholder ``.../123456/0.123456.1234`` (symptom of a
failed DOI creation at publish time).

Context: https://github.com/dandi/dandi-archive/issues/2759
"""

from __future__ import annotations

import difflib
import json
import re

from django.core.files.storage import default_storage
import djclick as click
from rest_framework.renderers import JSONRenderer
from tqdm import tqdm

from dandiapi.api import doi as doi_module
from dandiapi.api.manifests import _assets_jsonld_path, _dandiset_jsonld_path
from dandiapi.api.models import Version
from dandiapi.api.tasks import write_manifest_files

# Matches the placeholder DOI that the publish code injects purely for schema
# validation (see dandiapi/api/services/publish/__init__.py and
# dandiapi/api/services/metadata/__init__.py).
_DUMMY_DOI_RE = re.compile(r'\.123456/0\.123456\.1234$')

VERSION_CHOICES = ('draft', 'published', 'all')
TARGET_CHOICES = ('dandiset', 'assets', 'both')


def _is_dummy_doi(doi: str | None) -> bool:
    return bool(doi) and bool(_DUMMY_DOI_RE.search(doi))


def _read_s3_bytes(path: str) -> bytes | None:
    """Return the bytes at ``path`` in the default storage, or None if missing."""
    if not default_storage.exists(path):
        return None
    with default_storage.open(path) as f:
        return f.read()


def _iter_asset_full_metadata(version: Version) -> list[dict]:
    return [
        asset.full_metadata
        for asset in version.assets.select_related('blob', 'zarr', 'zarr__dandiset').iterator()
    ]


def _renormalize(obj: object) -> object:
    """Round-trip ``obj`` through ``JSONRenderer`` and ``json.loads``.

    Ensures comparisons with parsed-from-S3 data are not tripped by
    ``Decimal``/``UUID``/``datetime`` or other DRF-specific coercions that
    ``json.loads`` would otherwise see only on one side.
    """
    return json.loads(JSONRenderer().render(obj))


def _diff(expected: object, actual: object, label: str) -> str:
    expected_s = json.dumps(expected, indent=2, sort_keys=True).splitlines(keepends=True)
    actual_s = json.dumps(actual, indent=2, sort_keys=True).splitlines(keepends=True)
    return ''.join(
        difflib.unified_diff(
            actual_s,
            expected_s,
            fromfile=f'{label} (S3)',
            tofile=f'{label} (expected from DB)',
            n=3,
        )
    )


def _dandiset_jsonld_matches(version: Version, *, show_diff: bool) -> tuple[bool, str]:
    path = _dandiset_jsonld_path(version)
    s3_bytes = _read_s3_bytes(path)
    if s3_bytes is None:
        return False, f'  {path}: MISSING on S3'

    try:
        s3_obj = json.loads(s3_bytes)
    except json.JSONDecodeError as e:
        return False, f'  {path}: unparsable on S3 ({e})'

    expected_obj = _renormalize(version.metadata)
    if s3_obj == expected_obj:
        return True, ''

    msg = f'  {path}: differs'
    if show_diff:
        msg += '\n' + _diff(expected_obj, s3_obj, 'dandiset.jsonld')
    return False, msg


def _assets_jsonld_matches(version: Version, *, show_diff: bool) -> tuple[bool, str]:
    path = _assets_jsonld_path(version)
    s3_bytes = _read_s3_bytes(path)
    if s3_bytes is None:
        return False, f'  {path}: MISSING on S3'

    try:
        s3_obj = json.loads(s3_bytes)
    except json.JSONDecodeError as e:
        return False, f'  {path}: unparsable on S3 ({e})'

    expected_obj = _renormalize(_iter_asset_full_metadata(version))
    if s3_obj == expected_obj:
        return True, ''

    msg = f'  {path}: differs ({len(s3_obj)} assets on S3, {len(expected_obj)} expected)'
    if show_diff:
        msg += '\n' + _diff(expected_obj, s3_obj, 'assets.jsonld')
    return False, msg


def _fix_missing_doi(version: Version, *, dry_run: bool) -> tuple[bool, str]:
    """Re-mint the DOI for a published Version whose DOI is missing/placeholder.

    Returns (changed, message).
    """
    if version.version == 'draft':
        return False, ''
    if version.doi and not _is_dummy_doi(version.doi):
        return False, ''

    reason = 'NULL' if not version.doi else 'placeholder'
    if dry_run:
        return True, f'  DOI would be re-minted ({reason})'

    try:
        new_doi = doi_module.create_doi(version)
    except Exception as e:  # noqa: BLE001
        # ``doi.create_doi`` (via ``_generate_doi_data``) mutates
        # ``version.metadata['doi']`` as a side effect *before* the HTTP call.
        # On failure that mutation is left behind on the in-memory instance,
        # which would then make the immediately-following compare-to-S3 step
        # report a spurious mismatch. Re-load from the DB to discard it.
        version.refresh_from_db()
        return False, f'  DOI remint FAILED ({reason}): {e}'

    # Save doi column; Version.save() re-populates metadata with the real DOI
    # and a DOI-based citation.
    version.doi = new_doi
    version.save()
    return True, f'  DOI re-minted ({reason}) -> {new_doi}'


def _select_versions(
    dandisets: tuple[int, ...],
    *,
    include_all: bool,
    version_filter: str,
    specific_version: str | None,
):
    qs = Version.objects.select_related('dandiset')

    if dandisets:
        qs = qs.filter(dandiset_id__in=dandisets)
    # else: --all was specified (mutual-exclusion is enforced by the caller),
    # so the queryset stays unfiltered by dandiset.

    if specific_version:
        qs = qs.filter(version=specific_version)
    elif version_filter == 'draft':
        qs = qs.filter(version='draft')
    elif version_filter == 'published':
        qs = qs.exclude(version='draft')
    elif version_filter == 'all':
        pass
    else:  # pragma: no cover - click.Choice enforces this
        raise click.ClickException(f'Unknown --version filter {version_filter!r}')

    return qs.order_by('dandiset_id', 'version')


@click.command()
@click.argument('dandisets', type=click.INT, nargs=-1)
@click.option(
    '-a',
    '--all',
    'include_all',
    is_flag=True,
    help='Run on all dandisets (mutually exclusive with positional dandiset IDs).',
)
@click.option(
    '--version',
    'version_filter',
    type=click.Choice(VERSION_CHOICES),
    default='all',
    show_default=True,
    help='Which versions to consider.',
)
@click.option(
    '--specific-version',
    'specific_version',
    default=None,
    help='Limit to a single version string (e.g. "draft" or "0.250917.2023"). Overrides --version.',
)
@click.option(
    '--targets',
    type=click.Choice(TARGET_CHOICES),
    default='dandiset',
    show_default=True,
    help='Which manifest files to compare: "dandiset" (dandiset.jsonld only, '
    'cheap), "assets" (assets.jsonld only, expensive), or "both".',
)
@click.option(
    '--dry-run',
    '--check',
    'dry_run',
    is_flag=True,
    default=False,
    help="Don't write anything; just report versions that would be updated.",
)
@click.option(
    '--sync/--async',
    'run_sync',
    default=False,
    show_default=True,
    help='Run write_manifest_files inline (--sync) or enqueue via celery (--async, default).',
)
@click.option(
    '--fix-doi/--no-fix-doi',
    'fix_doi',
    default=True,
    show_default=True,
    help='Also re-mint DOIs for published versions whose version.doi is NULL or a placeholder.',
)
@click.option(
    '--show-diff',
    is_flag=True,
    default=False,
    help='Show a unified diff when a manifest differs (implies verbose output).',
)
def sync_manifest_files(  # noqa: C901, PLR0912, PLR0913, PLR0915
    dandisets: tuple[int, ...],
    *,
    include_all: bool,
    version_filter: str,
    specific_version: str | None,
    targets: str,
    dry_run: bool,
    run_sync: bool,
    fix_doi: bool,
    show_diff: bool,
):
    """
    Reconcile S3 manifests with the database.

    For each selected Version, compares the on-S3 dandiset.jsonld and/or
    assets.jsonld to what would be generated from the current database state.
    If they differ (or the S3 object is missing), the full set of manifest
    files for that version is regenerated via ``write_manifest_files``. By
    default the regeneration is enqueued via Celery (use ``--sync`` to run
    inline).

    Optionally (on by default) re-mint DOIs for published versions whose
    ``version.doi`` column is NULL or is the publishing-time placeholder
    (...`.123456/0.123456.1234`).

    Motivated by https://github.com/dandi/dandi-archive/issues/2759.
    """
    if bool(dandisets) == include_all:
        raise click.ClickException("Must specify exactly one of 'dandisets' or --all")

    if specific_version and version_filter != 'all':
        click.echo('Note: --specific-version overrides --version', err=True)

    compare_dandiset = targets in ('dandiset', 'both')
    compare_assets = targets in ('assets', 'both')

    versions_qs = _select_versions(
        dandisets,
        include_all=include_all,
        version_filter=version_filter,
        specific_version=specific_version,
    )

    total = versions_qs.count()
    if total == 0:
        click.echo('No matching versions.')
        return

    click.echo(
        f'Checking {total} version(s) '
        f'(targets={targets}, dry_run={dry_run}, '
        f'async={not run_sync}, fix_doi={fix_doi}).'
    )

    n_doi_fixed = 0
    n_doi_would_fix = 0
    n_manifest_mismatch = 0
    n_manifest_regen = 0
    n_regen_failed = 0

    for version in tqdm(versions_qs.iterator(), total=total):
        label = f'{version.dandiset.identifier}/{version.version}'
        messages: list[str] = []
        need_regen = False

        # 1) DOI fix (only for published versions; draft versions have no DOI,
        # and skip if doi already looks OK).
        if (
            fix_doi
            and version.version != 'draft'
            and (not version.doi or _is_dummy_doi(version.doi))
        ):
            changed, msg = _fix_missing_doi(version, dry_run=dry_run)
            if msg:
                messages.append(msg)
            if changed:
                if dry_run:
                    n_doi_would_fix += 1
                else:
                    n_doi_fixed += 1
                # DOI fix updates metadata -> manifest definitely needs rewrite
                need_regen = True

        # 2) Compare manifests
        if compare_dandiset:
            matches, msg = _dandiset_jsonld_matches(version, show_diff=show_diff)
            if not matches:
                need_regen = True
                n_manifest_mismatch += 1
                messages.append(msg)

        if compare_assets:
            matches, msg = _assets_jsonld_matches(version, show_diff=show_diff)
            if not matches:
                need_regen = True
                n_manifest_mismatch += 1
                messages.append(msg)

        if not need_regen:
            continue

        if dry_run:
            messages.append('  -> would regenerate all manifest files')
        else:
            try:
                if run_sync:
                    write_manifest_files(version.id)
                else:
                    write_manifest_files.delay(version.id)
                n_manifest_regen += 1
                messages.append(
                    '  -> regenerated all manifest files'
                    if run_sync
                    else '  -> enqueued manifest regeneration'
                )
            except Exception as e:  # noqa: BLE001
                n_regen_failed += 1
                messages.append(f'  -> regeneration FAILED: {e}')

        click.echo(f'{label}:')
        for m in messages:
            click.echo(m)

    click.echo('')
    click.echo('Summary:')
    click.echo(f'  versions checked:       {total}')
    click.echo(f'  manifest mismatches:    {n_manifest_mismatch}')
    if dry_run:
        click.echo(f'  DOIs to re-mint:        {n_doi_would_fix}')
        click.echo('  (dry run: no changes made)')
    else:
        click.echo(f'  DOIs re-minted:         {n_doi_fixed}')
        click.echo(
            f'  manifest regenerations: {n_manifest_regen} ({"sync" if run_sync else "enqueued"})'
        )
        if n_regen_failed:
            click.echo(f'  regeneration failures:  {n_regen_failed}')
