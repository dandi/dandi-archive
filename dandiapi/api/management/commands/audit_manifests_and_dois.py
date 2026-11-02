from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import TYPE_CHECKING, Any

from django.core.files.storage import default_storage
import djclick as click
from tqdm import tqdm
import yaml

from dandiapi.api.manifests import (
    _assets_jsonld_path,
    _assets_yaml_path,
    _collection_jsonld_path,
    _dandiset_jsonld_path,
    _dandiset_yaml_path,
    _manifests_path,
    all_manifest_filepaths,
    write_assets_jsonld,
    write_assets_yaml,
    write_collection_jsonld,
    write_dandiset_jsonld,
    write_dandiset_yaml,
)
from dandiapi.api.models import Version

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterator

    from django.db.models import QuerySet

logger = logging.getLogger(__name__)


def _manifests_embedding_metadata(version: Version) -> Iterator[tuple[str, Callable[[Any], Any]]]:
    """Yield the manifest files written from `version.metadata`, with their parsers.

    These are the only manifests which embed the DOI; the asset and collection
    manifests are unaffected.
    """
    yield _dandiset_jsonld_path(version), json.load
    yield _dandiset_yaml_path(version), yaml.safe_load


def missing_manifest_paths(version: Version) -> list[str]:
    """Return the manifest paths of `version` which aren't present in storage.

    This covers every manifest, not just the two written from the version metadata.
    """
    # Every manifest of a version lives in the same prefix, so one listing answers for all
    # of them, and basenames are enough to compare against.
    _, existing_filenames = default_storage.listdir(_manifests_path(version))
    existing = set(existing_filenames)

    return [
        path for path in all_manifest_filepaths(version) if path.rsplit('/', 1)[-1] not in existing
    ]


def missing_manifest_dois(version: Version, skip: Collection[str] = ()) -> dict[str, str]:
    """Map `version`'s manifests which don't carry its metadata DOI to what they carry instead.

    Manifests in `skip` aren't inspected, so that manifests already reported as missing
    aren't reported twice. A manifest which can't be read or parsed is reported as such,
    since its DOI can't be confirmed either way.
    """
    expected_doi = version.metadata.get('doi')

    discrepancies: dict[str, str] = {}
    for path, load in _manifests_embedding_metadata(version):
        if path in skip:
            continue

        try:
            with default_storage.open(path) as manifest_file:
                metadata = load(manifest_file)
            manifest_doi = metadata.get('doi')
        except Exception as e:  # noqa: BLE001
            logger.info('Could not read manifest %s: %s', path, e)
            discrepancies[path] = f'unreadable ({e})'
            continue

        if manifest_doi != expected_doi:
            discrepancies[path] = 'no DOI' if manifest_doi is None else f'DOI {manifest_doi}'

    return discrepancies


@dataclass
class VersionAudit:
    """What was found wrong with a single published version.

    A version can fall into more than one of the four cases.
    """

    version: Version

    # Case 1: manifest files which aren't present in storage at all.
    missing_manifests: list[str]
    # Case 2: manifests which don't carry the DOI from the version metadata, mapped to what
    # they carry instead. Only populated for versions whose metadata has a DOI.
    manifests_missing_doi: dict[str, str]
    # Case 3: the version row has a DOI, but the version metadata doesn't.
    metadata_missing_doi: bool
    # Case 4: the version row has no DOI.
    model_missing_doi: bool

    @property
    def has_problems(self) -> bool:
        return bool(
            self.missing_manifests
            or self.manifests_missing_doi
            or self.metadata_missing_doi
            or self.model_missing_doi
        )


def audit_version(version: Version, *, check_manifest_dois: bool = True) -> VersionAudit:
    """Check a single published version for all four cases.

    Clearing `check_manifest_dois` leaves out case 2, the only check which has to read the
    manifests back out of storage, for a run which reports case 1 alone.
    """
    missing_manifests = missing_manifest_paths(version)
    metadata_doi = version.metadata.get('doi')

    return VersionAudit(
        version=version,
        missing_manifests=missing_manifests,
        # Without a DOI in the metadata there's nothing to compare the manifests against;
        # such a version is reported under case 3 or case 4 instead.
        manifests_missing_doi=(
            missing_manifest_dois(version, skip=missing_manifests)
            if check_manifest_dois and metadata_doi
            else {}
        ),
        metadata_missing_doi=bool(version.doi) and not metadata_doi,
        model_missing_doi=not version.doi,
    )


def _manifest_writers(version: Version) -> dict[str, Callable[[Version], None]]:
    """Map each of `version`'s manifest paths to the function which writes it.

    Keying the writers by path is what lets only the broken manifests be rewritten, so that
    repairing a stale `dandiset.yaml` doesn't regenerate the version's asset manifests too.
    """
    return {
        _dandiset_jsonld_path(version): write_dandiset_jsonld,
        _assets_jsonld_path(version): write_assets_jsonld,
        _dandiset_yaml_path(version): write_dandiset_yaml,
        _assets_yaml_path(version): write_assets_yaml,
        _collection_jsonld_path(version): write_collection_jsonld,
    }


def rewrite_manifests(version: Version, paths: Collection[str]) -> None:
    """Rewrite the given manifest `paths` of `version`.

    They're written from the version's existing metadata, so this repairs cases 1 and 2
    only: a version whose DOI never made it into its metadata (case 3), or which has no DOI
    at all (case 4), can't be repaired this way.
    """
    writers = _manifest_writers(version)
    for path in all_manifest_filepaths(version):
        if path in paths:
            # A manifest added without a writer mapped for it raises here, rather than
            # being silently skipped.
            writers[path](version)


def _version_queryset(dandisets: tuple[int, ...], *, include_all: bool) -> QuerySet[Version]:
    """Return the published versions a subcommand's dandiset selection asks for."""
    if bool(dandisets) == include_all:
        raise click.ClickException("Must specify exactly one of 'dandisets' or --all")

    version_qs = (
        Version.objects.exclude(version='draft')
        .select_related('dandiset')
        .order_by('dandiset_id', 'version')
    )
    if dandisets:
        version_qs = version_qs.filter(dandiset_id__in=dandisets)

    return version_qs


def _audit_versions(
    version_qs: QuerySet[Version], *, check_manifest_dois: bool = True
) -> tuple[int, list[VersionAudit]]:
    """Audit every version in `version_qs`, returning the total scanned and the problem ones."""
    total_versions = version_qs.count()
    click.echo(f'Scanning {total_versions} published versions...')

    audits = []
    for version in tqdm(version_qs.iterator(), total=total_versions):
        audit = audit_version(version, check_manifest_dois=check_manifest_dois)
        if audit.has_problems:
            audits.append(audit)

    return total_versions, audits


def _report_missing_manifests(audits: list[VersionAudit]) -> None:
    """Enumerate case 1: versions with manifest files absent from storage."""
    missing_manifests = [audit for audit in audits if audit.missing_manifests]
    click.echo(f'\n1. Versions with missing manifest files: {len(missing_manifests)}')
    for audit in missing_manifests:
        click.echo(f'  {audit.version}')
        for path in audit.missing_manifests:
            click.echo(f'    {path}')


def _report_manifests_missing_doi(audits: list[VersionAudit]) -> None:
    """Enumerate case 2: versions whose manifests don't carry their metadata DOI."""
    manifests_missing_doi = [audit for audit in audits if audit.manifests_missing_doi]
    click.echo(
        f'\n2. Versions whose manifests are missing the DOI in their metadata: '
        f'{len(manifests_missing_doi)}'
    )
    for audit in manifests_missing_doi:
        click.echo(f'  {audit.version} (metadata DOI {audit.version.metadata["doi"]})')
        for path, found in audit.manifests_missing_doi.items():
            click.echo(f'    {path}: {found}')


def _report_metadata_missing_doi(audits: list[VersionAudit]) -> None:
    """Enumerate case 3: versions with a DOI absent from their own metadata."""
    metadata_missing_doi = [audit for audit in audits if audit.metadata_missing_doi]
    click.echo(
        f'\n3. Versions with a DOI on the version, but not in their metadata: '
        f'{len(metadata_missing_doi)}'
    )
    for audit in metadata_missing_doi:
        click.echo(f'  {audit.version} (DOI {audit.version.doi})')


def _report_model_missing_doi(audits: list[VersionAudit]) -> None:
    """Enumerate case 4: versions with no DOI at all."""
    model_missing_doi = [audit for audit in audits if audit.model_missing_doi]
    click.echo(f'\n4. Versions with no DOI on the version: {len(model_missing_doi)}')
    for audit in model_missing_doi:
        click.echo(f'  {audit.version}')


def _repair(targets: list[tuple[Version, list[str]]]) -> None:
    """Rewrite the given manifests of each version in `targets`."""
    if not targets:
        click.echo('\nNo manifests to rewrite.')
        return

    click.echo(f'\nRewriting the manifests of {len(targets)} versions...')
    rewritten = 0
    failed: list[Version] = []
    for version, paths in tqdm(targets):
        try:
            rewrite_manifests(version, paths)
        except Exception as e:
            # One unwritable version shouldn't abandon the rest; re-running the command
            # re-audits and picks up whatever is still broken.
            logger.exception('Could not rewrite the manifests of version %s', version)
            click.echo(f'  ERROR: could not rewrite {version}: {e}', err=True)
            failed.append(version)
        else:
            rewritten += len(paths)

    click.echo(f'Rewrote {rewritten} manifest files across {len(targets) - len(failed)} versions')
    if failed:
        click.echo(f'Failed to rewrite the manifests of {len(failed)} versions', err=True)


def _target_arguments(command: Callable) -> Callable:
    """Add the dandiset selection shared by every subcommand."""
    command = click.option(
        '-a',
        '--all',
        'include_all',
        is_flag=True,
        help='Run on all dandisets.',
    )(command)
    return click.argument(
        'dandisets',
        type=click.INT,
        nargs=-1,
    )(command)


def _rewrite_option(command: Callable) -> Callable:
    """Add the opt-in repair shared by the subcommands for the repairable cases."""
    return click.option(
        '--rewrite-manifests',
        'rewrite',
        is_flag=True,
        default=False,
        help='Rewrite the manifests reported by this subcommand, after reporting them.',
    )(command)


@click.group()
def audit_manifests_and_dois():
    """
    Audit published versions for missing manifests and missing DOIs.

    Publishing used to mint the DOI and write the manifest files in a race condition, so a
    manifest could be written before the DOI was saved, leaving `dandiset.jsonld`/`dandiset.yaml`
    on S3 without `doi` (and with a non-DOI `citation`).
    See https://github.com/dandi/dandi-archive/issues/2759.

    Four cases are enumerated, and a version may fall into more than one of them:

    1. Versions missing any of their manifest files in storage, asset and collection manifests
    included. Reported on its own by the `missing-manifests` subcommand.

    2. Versions with a DOI in their metadata which is missing from (or differs from the one in)
    their manifests. A manifest which exists but can't be read or parsed is reported here too,
    since its DOI can't be confirmed. Reported on its own by the `missing-manifest-dois`
    subcommand.

    3. Versions with a DOI on the version row which is missing from their metadata.

    4. Versions with no DOI on the version row at all, which is where a DOI has to come from.

    `report` enumerates all four. Cases 1 and 2 are the repairable ones, so they also have a
    subcommand of their own, and only those two take --rewrite-manifests. Nothing is written
    unless it's passed, so a plain run is a dry run of it.

    Only published versions are considered: drafts never have a DOI, and their manifests are
    rewritten whenever the draft is modified.
    """


@audit_manifests_and_dois.command('report')
@_target_arguments
def report(dandisets: tuple[int, ...], *, include_all: bool):
    """Report all four cases."""
    version_qs = _version_queryset(dandisets, include_all=include_all)
    total_versions, audits = _audit_versions(version_qs)
    if not audits:
        click.echo(f'No problems found in {total_versions} published versions.')
        return

    _report_missing_manifests(audits)
    _report_manifests_missing_doi(audits)
    _report_metadata_missing_doi(audits)
    _report_model_missing_doi(audits)
    click.echo(
        f'\nScanned {total_versions} published versions; {len(audits)} fall into at least one case.'
    )


@audit_manifests_and_dois.command('missing-manifests')
@_target_arguments
@_rewrite_option
def missing_manifests(dandisets: tuple[int, ...], *, include_all: bool, rewrite: bool):
    """
    Enumerate case 1 alone: versions with manifest files missing from storage.

    --rewrite-manifests writes the missing manifests, and only those: a manifest which is
    present but missing its DOI is case 2, and is left to `missing-manifest-dois`.
    """
    version_qs = _version_queryset(dandisets, include_all=include_all)
    # Case 2 is the only check which reads the manifests back, and it isn't reported here.
    _, audits = _audit_versions(version_qs, check_manifest_dois=False)
    _report_missing_manifests(audits)

    if rewrite:
        _repair(
            [
                (audit.version, audit.missing_manifests)
                for audit in audits
                if audit.missing_manifests
            ]
        )


@audit_manifests_and_dois.command('missing-manifest-dois')
@_target_arguments
@_rewrite_option
def missing_manifest_dois_command(dandisets: tuple[int, ...], *, include_all: bool, rewrite: bool):
    """
    Enumerate case 2 alone: versions whose manifests don't carry the DOI in their metadata.

    --rewrite-manifests writes those manifests from the version's metadata, and only those:
    a manifest missing from storage altogether is case 1, and is left to `missing-manifests`.
    """
    version_qs = _version_queryset(dandisets, include_all=include_all)
    _, audits = _audit_versions(version_qs)
    _report_manifests_missing_doi(audits)

    if rewrite:
        # Only `dandiset.jsonld` and `dandiset.yaml` embed the DOI, so those are the only
        # paths case 2 ever reports, and so the only ones rewritten here. The version's asset
        # and collection manifests don't carry a DOI and are left alone.
        _repair(
            [
                (audit.version, list(audit.manifests_missing_doi))
                for audit in audits
                if audit.manifests_missing_doi
            ]
        )
