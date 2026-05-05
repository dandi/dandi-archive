"""Seed a matrix of dandisets that exercises every advanced-search operator.

Idempotent — re-running deletes any prior dandisets it created (those whose
draft-version name starts with ``Search Test``) and recreates them.

Usage:
    ./manage.py create_search_test_data --owner you@example.com
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from dandischema.consts import DANDI_SCHEMA_VERSION
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
import djclick as click

from dandiapi.api.models import AssetBlob, Dandiset, Version
from dandiapi.api.services.asset import add_asset_to_version
from dandiapi.api.services.dandiset import create_open_dandiset
from dandiapi.api.services.metadata import validate_asset_metadata, validate_version_metadata
from dandiapi.api.tasks import calculate_sha256

_TEST_PREFIX = 'Search Test'


def _ts(date: str) -> datetime:
    return datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=UTC)


def _make_blob(*, content: bytes, etag: str) -> AssetBlob:
    """Create or fetch an AssetBlob with a deterministic etag."""
    try:
        return AssetBlob.objects.get(etag=etag)
    except AssetBlob.DoesNotExist:
        blob = AssetBlob.objects.create(
            blob_id=uuid4(),
            blob=SimpleUploadedFile(name=f'{etag}.bin', content=content),
            etag=etag,
            size=len(content),
        )
        calculate_sha256(blob_id=blob.blob_id)
        blob.refresh_from_db()
        return blob


def _backdate_dandiset(dandiset: Dandiset, *, created: datetime) -> None:
    Dandiset.objects.filter(pk=dandiset.pk).update(created=created)


def _backdate_version(version: Version, *, created: datetime, modified: datetime) -> None:
    Version.objects.filter(pk=version.pk).update(created=created, modified=modified)


def _build_asset_metadata(  # noqa: PLR0913
    *,
    path: str,
    encoding_format: str,
    species: str | None = None,
    approach: str | None = None,
    technique: str | None = None,
    standard: str | None = None,
) -> dict:
    metadata: dict = {
        'schemaVersion': DANDI_SCHEMA_VERSION,
        'schemaKey': 'Asset',
        'encodingFormat': encoding_format,
        'path': path,
    }
    if species is not None:
        metadata['wasAttributedTo'] = [{'schemaKey': 'Participant', 'species': {'name': species}}]
    if approach is not None:
        metadata['approach'] = [{'name': approach}]
    if technique is not None:
        metadata['measurementTechnique'] = [{'name': technique}]
    if standard is not None:
        metadata['dataStandard'] = [{'name': standard}]
    return metadata


def _add_published_copy(
    *, dandiset: Dandiset, draft: Version, version_str: str, published_created: datetime
) -> Version:
    """Create a published Version cloning the draft's metadata + assets, backdated."""
    published = Version.objects.create(
        dandiset=dandiset,
        name=draft.name,
        version=version_str,
        metadata={**draft.metadata, 'version': version_str},
        status=Version.Status.PUBLISHED,
    )
    for asset in draft.assets.all():
        published.assets.add(asset)
    _backdate_version(published, created=published_created, modified=published_created)
    return published


# Each row: (suffix, dandiset_created, draft_modified, published_version_date, assets)
# `assets` is a list of dicts passed to _build_asset_metadata.
_SCENARIOS: list[dict] = [
    {
        'tag': 'A-old-mouse-ephys',
        'created': _ts('2023-01-01'),
        'modified': _ts('2023-06-01'),
        'published': None,
        'assets': [
            {
                'path': 'A/recording.nwb',
                'encoding_format': 'application/x-nwb',
                # Real DANDI uses "Mus musculus - House mouse" or just "House mouse"
                'species': 'Mus musculus - House mouse',
                'approach': 'electrophysiological approach',
                'technique': 'spike sorting technique',
                'standard': 'Neurodata Without Borders (NWB)',
            },
        ],
    },
    {
        'tag': 'B-rat-published-2024',
        'created': _ts('2024-06-15'),
        'modified': _ts('2026-04-15'),
        'published': _ts('2024-12-01'),
        'assets': [
            {
                'path': 'B/behavior.nwb',
                'encoding_format': 'application/x-nwb',
                'species': 'Rattus norvegicus - Norway rat',
                'approach': 'behavioral approach',
                'technique': 'behavioral technique',
                'standard': 'Neurodata Without Borders (NWB)',
            },
        ],
    },
    {
        'tag': 'C-human-imaging-published-2025',
        'created': _ts('2025-03-10'),
        'modified': _ts('2025-03-10'),
        'published': _ts('2025-03-10'),
        'assets': [
            {
                'path': 'C/scan.tif',
                'encoding_format': 'image/tiff',
                'species': 'Human',
                'approach': 'microscopy approach',
                'technique': 'surgical technique',
                'standard': 'Brain Imaging Data Structure (BIDS)',
            },
        ],
    },
    {
        'tag': 'D-bare-text',
        'created': _ts('2026-01-20'),
        'modified': _ts('2026-04-20'),
        'published': None,
        'assets': [
            {
                'path': 'D/notes.txt',
                'encoding_format': 'text/plain',
            },
        ],
    },
    {
        'tag': 'E-mouse-video',
        'created': _ts('2024-09-01'),
        'modified': _ts('2024-09-01'),
        'published': None,
        'assets': [
            {
                'path': 'E/clip.mp4',
                'encoding_format': 'video/mp4',
                'species': 'House mouse',
                'approach': 'electrophysiological approach',
                'standard': 'Neurodata Without Borders (NWB)',
            },
        ],
    },
]


def _delete_existing() -> int:
    """Drop dandisets named with the test prefix so reruns are idempotent.

    Bypasses ``delete_dandiset`` (which forbids deleting published-version
    dandisets) — this is a dev seeder, raw ORM is fine.
    """
    drafts = Version.objects.filter(version='draft', metadata__name__startswith=_TEST_PREFIX)
    dandiset_ids = list(drafts.values_list('dandiset_id', flat=True).distinct())
    Dandiset.objects.filter(id__in=dandiset_ids).delete()
    return len(dandiset_ids)


@click.command()
@click.option('--owner', 'email', required=True, help='Email address of the owning superuser')
def create_search_test_data(email: str) -> None:
    owner = User.objects.get(email=email)

    removed = _delete_existing()
    if removed:
        click.echo(f'Removed {removed} existing test dandiset(s).')

    for scenario in _SCENARIOS:
        name = f'{_TEST_PREFIX} {scenario["tag"]}'
        dandiset, draft = create_open_dandiset(
            user=owner,
            version_name=name,
            version_metadata={
                'description': f'Search test fixture: {scenario["tag"]}',
            },
        )

        for asset_spec in scenario['assets']:
            etag = f'{uuid4().hex}-0'
            blob = _make_blob(content=b'X' * 32, etag=etag)
            asset = add_asset_to_version(
                user=owner,
                version=draft,
                asset_blob=blob,
                metadata=_build_asset_metadata(**asset_spec),
            )
            validate_asset_metadata(asset=asset)

        validate_version_metadata(version=draft)

        # Backdate the draft version (created tracks the seed date too)
        _backdate_version(draft, created=scenario['created'], modified=scenario['modified'])

        if scenario['published'] is not None:
            published_str = scenario['published'].strftime('0.%y%m%d.') + '1200'
            _add_published_copy(
                dandiset=dandiset,
                draft=draft,
                version_str=published_str,
                published_created=scenario['published'],
            )

        # Backdate the dandiset itself
        _backdate_dandiset(dandiset, created=scenario['created'])

        click.echo(f'  created {dandiset.identifier}: {name}')

    # The asset_search materialized view powers has_species/has_approach/etc.
    with connection.cursor() as cursor:
        cursor.execute('REFRESH MATERIALIZED VIEW asset_search;')
    click.echo('Refreshed asset_search materialized view.')
