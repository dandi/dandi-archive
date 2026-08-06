from __future__ import annotations

import json

import click
from django.core.files.storage import default_storage
import pytest

from dandiapi.api import doi as doi_module
from dandiapi.api.management.commands.sync_manifest_files import (
    _is_dummy_doi,
    sync_manifest_files,
)
from dandiapi.api.manifests import _assets_jsonld_path, _dandiset_jsonld_path
from dandiapi.api.models import Version
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.tasks import write_manifest_files
from dandiapi.api.tests.factories import (
    DandisetFactory,
    DraftVersionFactory,
    PublishedAssetFactory,
    PublishedVersionFactory,
)

# A deterministic synthetic DOI used for tests that exercise the DOI-remint
# code path. The real ``doi.create_doi`` runs ``to_datacite()`` which performs
# full ``PublishedDandiset`` pydantic validation; faker-generated metadata
# does not satisfy that schema, so we monkeypatch ``create_doi`` rather than
# relying on the offline-mode shortcut to short-circuit it.
_FAKE_DOI = '10.80507/dandi.000001/0.250506.1234'


def _read_jsonld(path: str):
    with default_storage.open(path) as f:
        return json.loads(f.read())


def _seed(version: Version) -> None:
    """Render and upload the full set of manifest files for ``version``."""
    write_manifest_files(version.id)


def _install_fake_create_doi(monkeypatch, value: str = _FAKE_DOI) -> None:
    """Replace ``doi.create_doi`` with a deterministic, no-op shim.

    Mirrors the side effect the real function has on ``version.metadata``
    via ``_generate_doi_data`` so subsequent ``Version.save()`` calls see
    the same in-memory state they would in production.
    """

    def _shim(version):
        version.metadata['doi'] = value
        return value

    monkeypatch.setattr(doi_module, 'create_doi', _shim)


# ---------------------------------------------------------------------------
# Pure-unit tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        (None, False),
        ('', False),
        ('10.48324/dandi.000027/0.210831.2033', False),
        ('10.80507/dandi.123456/0.123456.1234', True),
        ('10.48324/dandi.123456/0.123456.1234', True),
        # The suffix anchor (``\.1234$``) means an additional trailing digit
        # disqualifies it.
        ('10.80507/dandi.123456/0.123456.12345', False),
    ],
)
def test_is_dummy_doi(value, expected):
    assert _is_dummy_doi(value) is expected


# ---------------------------------------------------------------------------
# Integration tests: MinIO + Django DB + eager Celery
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_change_when_in_sync(draft_asset_factory, capsys):
    """When S3 matches the DB, the command must not rewrite anything."""
    version = DraftVersionFactory.create()
    version.assets.add(draft_asset_factory())
    _seed(version)

    path = _dandiset_jsonld_path(version)
    before = _read_jsonld(path)

    sync_manifest_files(str(version.dandiset_id), '--targets', 'dandiset')

    assert _read_jsonld(path) == before
    out = capsys.readouterr().out
    assert 'manifest mismatches:    0' in out


@pytest.mark.django_db
def test_detects_and_repairs_drift_in_dandiset_jsonld(draft_asset_factory):
    """If the on-S3 manifest is stale, the command must regenerate it."""
    version = DraftVersionFactory.create()
    version.assets.add(draft_asset_factory())
    _seed(version)

    path = _dandiset_jsonld_path(version)
    assert 'NEW DESCRIPTION' not in (_read_jsonld(path).get('description') or '')

    version.metadata['description'] = 'NEW DESCRIPTION'
    version.save()
    version.refresh_from_db()

    sync_manifest_files(str(version.dandiset_id), '--targets', 'dandiset')

    after = _read_jsonld(path)
    assert after['description'] == 'NEW DESCRIPTION'
    assert after == version.metadata


@pytest.mark.django_db
def test_dry_run_does_not_write(draft_asset_factory, capsys):
    version = DraftVersionFactory.create()
    version.assets.add(draft_asset_factory())
    _seed(version)

    path = _dandiset_jsonld_path(version)
    snapshot = _read_jsonld(path)

    version.metadata['description'] = 'WOULD BE WRITTEN'
    version.save()

    sync_manifest_files(
        str(version.dandiset_id),
        '--targets',
        'dandiset',
        '--dry-run',
    )

    # S3 is untouched
    assert _read_jsonld(path) == snapshot
    # ... but the command reported what it would have done
    out = capsys.readouterr().out
    assert 'would regenerate' in out


@pytest.mark.django_db
def test_missing_s3_object_treated_as_mismatch(draft_asset_factory):
    version = DraftVersionFactory.create()
    version.assets.add(draft_asset_factory())
    _seed(version)

    path = _dandiset_jsonld_path(version)
    default_storage.delete(path)
    assert not default_storage.exists(path)

    sync_manifest_files(str(version.dandiset_id), '--targets', 'dandiset')

    assert default_storage.exists(path)
    assert _read_jsonld(path) == version.metadata


@pytest.mark.django_db
def test_targets_assets_compares_assets_jsonld():
    version = DraftVersionFactory.create()
    version.assets.add(PublishedAssetFactory.create())
    _seed(version)

    assets_path = _assets_jsonld_path(version)
    assert _read_jsonld(assets_path) == [a.full_metadata for a in version.assets.all()]

    # Add a new asset so DB and S3 diverge for assets.jsonld.
    version.assets.add(PublishedAssetFactory.create())

    sync_manifest_files(str(version.dandiset_id), '--targets', 'assets')

    assert _read_jsonld(assets_path) == [a.full_metadata for a in version.assets.all()]


@pytest.mark.django_db
def test_targets_both_regenerates_when_either_differs():
    """``--targets=both`` must regenerate if either of the two manifests is stale."""
    version = DraftVersionFactory.create()
    version.assets.add(PublishedAssetFactory.create())
    _seed(version)

    dandiset_path = _dandiset_jsonld_path(version)
    assets_path = _assets_jsonld_path(version)
    dandiset_before = _read_jsonld(dandiset_path)

    # Drift only on the dandiset side; assets.jsonld is still in sync.
    version.metadata['description'] = 'BOTH-MODE DRIFT'
    version.save()

    sync_manifest_files(str(version.dandiset_id), '--targets', 'both')

    # dandiset.jsonld got the update
    after = _read_jsonld(dandiset_path)
    assert after != dandiset_before
    assert after['description'] == 'BOTH-MODE DRIFT'
    # assets.jsonld is still consistent with the DB (write_manifest_files
    # rewrites all five anyway, so this exercises that path too).
    assert _read_jsonld(assets_path) == [a.full_metadata for a in version.assets.all()]


@pytest.mark.django_db
def test_doi_remint_fills_null_doi_on_published_version(monkeypatch):
    """A published version with a NULL doi should be re-minted by default."""
    _install_fake_create_doi(monkeypatch)

    version = PublishedVersionFactory.create(doi=None)
    version.metadata.pop('doi', None)
    Version.objects.filter(id=version.id).update(metadata=version.metadata)
    _seed(version)
    version.refresh_from_db()
    assert version.doi is None

    sync_manifest_files(str(version.dandiset_id), '--version', 'published')

    version.refresh_from_db()
    assert version.doi == _FAKE_DOI
    s3 = _read_jsonld(_dandiset_jsonld_path(version))
    assert s3.get('doi') == _FAKE_DOI
    assert _FAKE_DOI in s3.get('citation', '')


@pytest.mark.django_db
def test_doi_remint_replaces_placeholder_doi(monkeypatch):
    _install_fake_create_doi(monkeypatch)

    placeholder = '10.80507/dandi.123456/0.123456.1234'
    version = PublishedVersionFactory.create(doi=placeholder)
    version.metadata['doi'] = placeholder
    Version.objects.filter(id=version.id).update(metadata=version.metadata)
    _seed(version)

    sync_manifest_files(str(version.dandiset_id), '--version', 'published')

    version.refresh_from_db()
    assert version.doi == _FAKE_DOI
    assert not _is_dummy_doi(version.doi)


@pytest.mark.django_db
def test_no_fix_doi_skips_doi_repair():
    """``--no-fix-doi`` must leave a NULL DOI untouched even on a published version."""
    version = PublishedVersionFactory.create(doi=None)
    version.metadata.pop('doi', None)
    Version.objects.filter(id=version.id).update(metadata=version.metadata)
    _seed(version)

    sync_manifest_files(
        str(version.dandiset_id),
        '--version',
        'published',
        '--no-fix-doi',
    )

    version.refresh_from_db()
    assert version.doi is None


@pytest.mark.django_db
def test_doi_remint_failure_is_reported_not_fatal(monkeypatch, capsys):
    version = PublishedVersionFactory.create(doi=None)
    version.metadata.pop('doi', None)
    Version.objects.filter(id=version.id).update(metadata=version.metadata)
    _seed(version)

    def _boom(_v):
        raise RuntimeError('datacite is on fire')

    monkeypatch.setattr(doi_module, 'create_doi', _boom)

    # Must not raise.
    sync_manifest_files(str(version.dandiset_id), '--version', 'published')

    out = capsys.readouterr().out
    assert 'DOI remint FAILED' in out

    version.refresh_from_db()
    assert version.doi is None


@pytest.mark.django_db
def test_version_filter_published_skips_drafts(draft_asset_factory):
    """``--version=published`` must not touch draft versions."""
    dandiset = DandisetFactory.create()
    draft = DraftVersionFactory.create(dandiset=dandiset)
    draft.assets.add(draft_asset_factory())
    published = PublishedVersionFactory.create(dandiset=dandiset)
    _seed(draft)
    _seed(published)

    draft_path = _dandiset_jsonld_path(draft)
    pub_path = _dandiset_jsonld_path(published)
    draft_before = _read_jsonld(draft_path)

    draft.metadata['description'] = 'STALE DRAFT'
    draft.save()
    published.metadata['description'] = 'STALE PUB'
    published.save()

    sync_manifest_files(
        str(dandiset.id),
        '--version',
        'published',
        '--no-fix-doi',
        '--targets',
        'dandiset',
    )

    assert _read_jsonld(draft_path) == draft_before
    assert _read_jsonld(pub_path)['description'] == 'STALE PUB'


@pytest.mark.django_db
def test_version_filter_draft_skips_published(draft_asset_factory):
    """``--version=draft`` must not touch published versions."""
    dandiset = DandisetFactory.create()
    draft = DraftVersionFactory.create(dandiset=dandiset)
    draft.assets.add(draft_asset_factory())
    published = PublishedVersionFactory.create(dandiset=dandiset)
    _seed(draft)
    _seed(published)

    draft_path = _dandiset_jsonld_path(draft)
    pub_path = _dandiset_jsonld_path(published)
    pub_before = _read_jsonld(pub_path)

    draft.metadata['description'] = 'STALE DRAFT'
    draft.save()
    published.metadata['description'] = 'STALE PUB'
    published.save()

    sync_manifest_files(
        str(dandiset.id),
        '--version',
        'draft',
        '--targets',
        'dandiset',
    )

    assert _read_jsonld(pub_path) == pub_before
    assert _read_jsonld(draft_path)['description'] == 'STALE DRAFT'


@pytest.mark.django_db
def test_specific_version_overrides_version_filter(draft_asset_factory):
    """``--specific-version=<ver>`` selects exactly that version, overriding --version."""
    dandiset = DandisetFactory.create()
    v1 = PublishedVersionFactory.create(dandiset=dandiset)
    v2 = PublishedVersionFactory.create(dandiset=dandiset)
    _seed(v1)
    _seed(v2)

    v1_path = _dandiset_jsonld_path(v1)
    v2_path = _dandiset_jsonld_path(v2)
    v2_before = _read_jsonld(v2_path)

    v1.metadata['description'] = 'V1 NEW'
    v1.save()
    v2.metadata['description'] = 'V2 NEW'
    v2.save()

    sync_manifest_files(
        str(dandiset.id),
        '--specific-version',
        v1.version,
        '--no-fix-doi',
        '--targets',
        'dandiset',
    )

    assert _read_jsonld(v1_path)['description'] == 'V1 NEW'
    # v2 is still the pre-update content on S3 (untouched by this run).
    assert _read_jsonld(v2_path) == v2_before


@pytest.mark.django_db
def test_dandiset_arg_filter_only_touches_named_dandiset(draft_asset_factory):
    a = DraftVersionFactory.create()
    b = DraftVersionFactory.create()
    a.assets.add(draft_asset_factory())
    b.assets.add(draft_asset_factory())
    _seed(a)
    _seed(b)

    a_path = _dandiset_jsonld_path(a)
    b_path = _dandiset_jsonld_path(b)
    b_before = _read_jsonld(b_path)

    a.metadata['description'] = 'A NEW'
    a.save()
    b.metadata['description'] = 'B NEW'
    b.save()

    sync_manifest_files(str(a.dandiset_id), '--targets', 'dandiset')

    assert _read_jsonld(a_path)['description'] == 'A NEW'
    assert _read_jsonld(b_path) == b_before


@pytest.mark.django_db
def test_all_flag_processes_every_dandiset(draft_asset_factory, capsys):
    """``--all`` with one stale and one in-sync dandiset: only the stale one regenerates."""
    stale = DraftVersionFactory.create()
    fresh = DraftVersionFactory.create()
    stale.assets.add(draft_asset_factory())
    fresh.assets.add(draft_asset_factory())
    _seed(stale)
    _seed(fresh)

    fresh_path = _dandiset_jsonld_path(fresh)
    fresh_snapshot = _read_jsonld(fresh_path)

    stale.metadata['description'] = 'STALE'
    stale.save()

    sync_manifest_files('--all', '--targets', 'dandiset', '--no-fix-doi')

    assert _read_jsonld(_dandiset_jsonld_path(stale))['description'] == 'STALE'
    assert _read_jsonld(fresh_path) == fresh_snapshot
    out = capsys.readouterr().out
    assert 'manifest mismatches:    1' in out


@pytest.mark.django_db
def test_show_diff_prints_unified_diff(draft_asset_factory, capsys):
    version = DraftVersionFactory.create()
    version.assets.add(draft_asset_factory())
    _seed(version)

    version.metadata['description'] = 'DIFF SHOULD APPEAR'
    version.save()

    sync_manifest_files(
        str(version.dandiset_id),
        '--targets',
        'dandiset',
        '--dry-run',
        '--show-diff',
    )

    out = capsys.readouterr().out
    assert 'dandiset.jsonld (S3)' in out
    assert 'dandiset.jsonld (expected from DB)' in out
    # Sanity: the diff body itself references the changed value
    assert 'DIFF SHOULD APPEAR' in out


@pytest.mark.django_db
def test_mutually_exclusive_args():
    """Either --all or dandiset IDs must be specified, not both, not neither."""
    with pytest.raises(click.ClickException):
        sync_manifest_files()  # neither

    with pytest.raises(click.ClickException):
        sync_manifest_files('--all', '1')  # both


@pytest.mark.django_db
def test_embargoed_manifest_is_re_tagged_on_regeneration(draft_asset_factory):
    version = DraftVersionFactory.create(
        dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED,
    )
    version.assets.add(draft_asset_factory())
    _seed(version)
    path = _dandiset_jsonld_path(version)
    assert default_storage.get_tags(path) == {'embargoed': 'true'}

    version.metadata['description'] = 'CHANGED'
    version.save()

    sync_manifest_files(str(version.dandiset_id), '--targets', 'dandiset')

    assert default_storage.get_tags(path) == {'embargoed': 'true'}
    assert _read_jsonld(path)['description'] == 'CHANGED'
