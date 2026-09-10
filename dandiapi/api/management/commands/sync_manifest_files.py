"""
Management command to reconcile manifest files on S3 against the database.

For each selected Version, compare what `dandiset.jsonld` and/or `assets.jsonld`
would be generated now from `version.metadata` / `version.assets` to what's
currently stored on S3. If they differ (or if the S3 object is missing),
trigger `write_manifest_files` to rewrite all manifest files for that version.

Optionally also repair DOIs for published versions whose `version.doi` is
NULL or equals the placeholder ``.../123456/0.123456.1234`` (symptom of a
failed DOI creation at publish time): adopt the DOI if it turns out to be
registered at DataCite already, otherwise mint it.

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

# Outcomes of the per-version DOI repair step.
DOI_SKIPPED = 'skipped'
DOI_WOULD_MINT = 'would-mint'
DOI_WOULD_ADOPT = 'would-adopt'
DOI_MINTED = 'minted'
DOI_ADOPTED = 'adopted'
DOI_FAILED = 'failed'


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


def _unadoptable_reason(version: Version, attributes: dict) -> str | None:
    """Say why an existing DataCite record must not be adopted, or None if it can be.

    Two ways a registered DOI is not the DOI we want to advertise:

    * it describes something else -- a misconfigured prefix or instance name
      would otherwise silently attach an unrelated DOI to this version. (A
      version published before ``DANDI_WEB_APP_URL`` last changed also lands
      here; that is a report-and-let-a-human-look case, not an auto-fix.)
    * it is still a DataCite ``draft``, which does not resolve. Publishing a
      dead doi.org link in the manifest is what we are trying to fix, not
      something to introduce. Promoting it would mean writing to DataCite,
      which this command deliberately never does.
    """
    expected_url = version.metadata.get('url')
    actual_url = attributes.get('url')
    if expected_url and actual_url and actual_url != expected_url:
        return f'it points at {actual_url} rather than {expected_url}'

    state = attributes.get('state')
    if state == 'draft':
        return 'it is still in DataCite "draft" state and would not resolve'

    return None


def _fix_missing_doi(version: Version, *, dry_run: bool) -> tuple[str, str]:  # noqa: PLR0911
    """Repair the DOI of a published Version whose DOI is missing/placeholder.

    The DOI string is deterministic, so a NULL ``version.doi`` does not mean
    there is no DOI: publish may have minted one and then failed to persist it
    (``services/publish`` logs exactly that). DataCite rejects a POST for an
    already-registered DOI, so look the DOI up first and adopt what is already
    there; only mint when nothing is registered.

    Returns ``(status, message)``, where status is one of ``DOI_SKIPPED``,
    ``DOI_WOULD_MINT``, ``DOI_WOULD_ADOPT``, ``DOI_MINTED``, ``DOI_ADOPTED``
    or ``DOI_FAILED``.
    """
    if version.version == 'draft':
        return DOI_SKIPPED, ''
    if version.doi and not _is_dummy_doi(version.doi):
        return DOI_SKIPPED, ''

    reason = 'NULL' if not version.doi else 'placeholder'
    expected_doi = doi_module.doi_for_version(version)

    # Read-only, so it runs under --dry-run too: that is what tells an operator
    # how many versions need a mint vs. only a DB write.
    try:
        existing = doi_module.get_doi(expected_doi)
    except Exception as e:  # noqa: BLE001
        return DOI_FAILED, f'  DOI lookup FAILED ({reason}) for {expected_doi}: {e}'

    if existing is not None:
        unadoptable = _unadoptable_reason(version, existing)
        if unadoptable:
            return DOI_FAILED, (
                f'  DOI {expected_doi} is registered at DataCite but {unadoptable}; not adopting'
            )
        if dry_run:
            return DOI_WOULD_ADOPT, f'  DOI would be adopted ({reason}) -> {expected_doi}'
        # Registered already: no DataCite write, just record it and let the
        # manifest be rewritten with the DOI and a doi.org citation.
        version.doi = expected_doi
        version.save()
        return DOI_ADOPTED, f'  DOI adopted from DataCite ({reason}) -> {expected_doi}'

    if dry_run:
        return DOI_WOULD_MINT, f'  DOI would be minted ({reason}) -> {expected_doi}'

    try:
        new_doi = doi_module.create_doi(version)
    except Exception as e:  # noqa: BLE001
        # ``doi.create_doi`` (via ``_generate_doi_data``) mutates
        # ``version.metadata['doi']`` as a side effect *before* the HTTP call.
        # On failure that mutation is left behind on the in-memory instance,
        # which would then make the immediately-following compare-to-S3 step
        # report a spurious mismatch. Re-load from the DB to discard it.
        version.refresh_from_db()
        return DOI_FAILED, f'  DOI mint FAILED ({reason}): {e}'

    # Save doi column; Version.save() re-populates metadata with the real DOI
    # and a DOI-based citation.
    version.doi = new_doi
    version.save()
    return DOI_MINTED, f'  DOI minted ({reason}) -> {new_doi}'


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
    help='Also repair DOIs for published versions whose version.doi is NULL or a placeholder '
    '(adopting an already-registered DataCite DOI in preference to minting a new one).',
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

    Optionally (on by default) repair DOIs for published versions whose
    ``version.doi`` column is NULL or is the publishing-time placeholder
    (...`.123456/0.123456.1234`). Because the DOI string is deterministic,
    such a version may already have its DOI registered at DataCite; that one
    is adopted (no DataCite write) and only a genuinely absent DOI is minted.

    Motivated by https://github.com/dandi/dandi-archive/issues/2759.
    """
    if bool(dandisets) == include_all:
        raise click.ClickException("Must specify exactly one of 'dandisets' or --all")

    if specific_version and version_filter != 'all':
        click.echo('Note: --specific-version overrides --version', err=True)

    compare_dandiset = targets in ('dandiset', 'both')
    compare_assets = targets in ('assets', 'both')

    # ``doi.create_doi`` computes the DOI string deterministically and only
    # *registers* it with DataCite when all DANDI_DOI_API_* settings are set.
    # Without them it would still return a well-formed DOI, which we would then
    # persist and publish in the manifests -- advertising a DOI that resolves
    # nowhere. That is worse than the NULL we are trying to repair, so refuse
    # to touch DOIs at all in that case.
    doi_unconfigured = fix_doi and not doi_module.doi_configured()
    if doi_unconfigured:
        fix_doi = False
        click.echo(
            'WARNING: DOI minting is not configured (DANDI_DOI_API_URL/USER/PASSWORD/PREFIX); '
            'skipping DOI repair. Manifests are still reconciled.',
            err=True,
        )

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

    n_doi_minted = 0
    n_doi_adopted = 0
    n_doi_would_mint = 0
    n_doi_would_adopt = 0
    n_doi_failed = 0
    n_manifest_mismatch = 0
    n_manifest_regen = 0
    n_regen_failed = 0

    for version in tqdm(versions_qs.iterator(), total=total):
        label = f'{version.dandiset.identifier}/{version.version}'
        messages: list[str] = []
        need_regen = False

        # 1) DOI fix. ``_fix_missing_doi`` itself skips draft versions and
        # versions whose DOI already looks fine.
        if fix_doi:
            status, msg = _fix_missing_doi(version, dry_run=dry_run)
            if msg:
                messages.append(msg)
            if status == DOI_WOULD_MINT:
                n_doi_would_mint += 1
                # DOI fix updates metadata -> manifest definitely needs rewrite
                need_regen = True
            elif status == DOI_WOULD_ADOPT:
                n_doi_would_adopt += 1
                need_regen = True
            elif status == DOI_MINTED:
                n_doi_minted += 1
                need_regen = True
            elif status == DOI_ADOPTED:
                n_doi_adopted += 1
                need_regen = True
            elif status == DOI_FAILED:
                n_doi_failed += 1

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

        if need_regen:
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

        # Report anything worth reporting -- in particular a failed DOI repair
        # on a version whose manifests are otherwise in sync.
        if not messages:
            continue

        click.echo(f'{label}:')
        for m in messages:
            click.echo(m)

    click.echo('')
    click.echo('Summary:')
    click.echo(f'  versions checked:       {total}')
    click.echo(f'  manifest mismatches:    {n_manifest_mismatch}')
    if dry_run:
        click.echo(f'  DOIs to mint:           {n_doi_would_mint}')
        click.echo(f'  DOIs to adopt:          {n_doi_would_adopt}')
        if n_doi_failed:
            click.echo(f'  DOI repair problems:    {n_doi_failed}')
        click.echo('  (dry run: no changes made)')
    else:
        click.echo(f'  DOIs minted:            {n_doi_minted}')
        click.echo(f'  DOIs adopted:           {n_doi_adopted}')
        if n_doi_failed:
            click.echo(f'  DOI repair failures:    {n_doi_failed}')
        click.echo(
            f'  manifest regenerations: {n_manifest_regen} ({"sync" if run_sync else "enqueued"})'
        )
        if n_regen_failed:
            click.echo(f'  regeneration failures:  {n_regen_failed}')
    if doi_unconfigured:
        click.echo('  (DOI repair skipped: DOI minting is not configured)')
