from __future__ import annotations

import json

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.forms.models import model_to_dict
import pytest
import yaml

from dandiapi.api.management.commands.audit_manifests_and_dois import (
    _version_queryset,
    audit_manifests_and_dois,
    audit_version,
    missing_manifest_dois,
    missing_manifest_paths,
)
from dandiapi.api.manifests import (
    _assets_jsonld_path,
    _assets_yaml_path,
    _collection_jsonld_path,
    _dandiset_jsonld_path,
    _dandiset_yaml_path,
    all_manifest_filepaths,
)
from dandiapi.api.models import Version
from dandiapi.api.tasks import write_manifest_files
from dandiapi.api.tests.factories import PublishedVersionFactory


def _written_manifests(version: Version) -> tuple[dict, dict]:
    with default_storage.open(_dandiset_jsonld_path(version)) as f:
        dandiset_jsonld = json.load(f)
    with default_storage.open(_dandiset_yaml_path(version)) as f:
        dandiset_yaml = yaml.safe_load(f)

    return dandiset_jsonld, dandiset_yaml


def _strip_metadata_doi(version: Version) -> None:
    """Remove the DOI from `version`'s metadata, leaving the DOI on the version row.

    `Version.save` repopulates `metadata['doi']` from `version.doi`, so the update has to
    bypass it.
    """
    Version.objects.filter(id=version.id).update(
        metadata={k: v for k, v in version.metadata.items() if k != 'doi'}
    )
    version.refresh_from_db()


@pytest.fixture
def version_with_doi_less_manifests():
    """Publish a version whose on-S3 manifests were written before its DOI was saved.

    This reproduces the dandi/dandi-archive#2759 race: the DOI is committed on the
    version, but the manifests still carry the pre-DOI metadata.
    """
    version: Version = PublishedVersionFactory.create()
    doi = version.doi

    # Write the manifests from a DOI-less version, exactly as the racing manifest task did.
    # `_populate_metadata` only ever adds `doi`, so it has to be stripped explicitly.
    version.doi = None
    version.metadata = {k: v for k, v in version.metadata.items() if k != 'doi'}
    version.save()
    write_manifest_files(version.id)

    # ...and only then save the minted DOI.
    version.doi = doi
    version.save()

    return version


# Case 1: missing manifests.


@pytest.mark.django_db
def test_missing_manifest_paths_detects_every_manifest():
    version: Version = PublishedVersionFactory.create()

    # No manifests have been written at all.
    assert missing_manifest_paths(version) == all_manifest_filepaths(version)


@pytest.mark.django_db
def test_missing_manifest_paths_detects_asset_manifests():
    version: Version = PublishedVersionFactory.create()
    write_manifest_files(version.id)
    default_storage.delete(_assets_yaml_path(version))
    default_storage.delete(_assets_jsonld_path(version))

    assert missing_manifest_paths(version) == [
        _assets_jsonld_path(version),
        _assets_yaml_path(version),
    ]


@pytest.mark.django_db
def test_missing_manifest_paths_ignores_present_manifests():
    version: Version = PublishedVersionFactory.create()
    write_manifest_files(version.id)

    assert missing_manifest_paths(version) == []


# Case 2: a DOI in the metadata which is missing from the manifests.


@pytest.mark.django_db
def test_missing_manifest_dois_detects_missing_doi(version_with_doi_less_manifests):
    version = version_with_doi_less_manifests

    assert missing_manifest_dois(version) == {
        _dandiset_jsonld_path(version): 'no DOI',
        _dandiset_yaml_path(version): 'no DOI',
    }


@pytest.mark.django_db
def test_missing_manifest_dois_ignores_current_manifests():
    version: Version = PublishedVersionFactory.create()
    write_manifest_files(version.id)

    assert missing_manifest_dois(version) == {}


@pytest.mark.django_db
def test_missing_manifest_dois_skips_requested_paths(version_with_doi_less_manifests):
    version = version_with_doi_less_manifests

    assert missing_manifest_dois(version, skip=[_dandiset_yaml_path(version)]) == {
        _dandiset_jsonld_path(version): 'no DOI'
    }


@pytest.mark.django_db
def test_missing_manifest_dois_reports_unreadable_manifest():
    version: Version = PublishedVersionFactory.create()
    write_manifest_files(version.id)
    default_storage.save(_dandiset_jsonld_path(version), ContentFile(b'not json'))

    [(path, found)] = missing_manifest_dois(version).items()
    assert path == _dandiset_jsonld_path(version)
    assert found.startswith('unreadable')


@pytest.mark.django_db
def test_missing_manifest_dois_reports_a_differing_doi():
    version: Version = PublishedVersionFactory.create()
    write_manifest_files(version.id)
    # Only the version row's DOI changes, so the manifests keep the DOI they were written with.
    old_doi = version.doi
    Version.objects.filter(id=version.id).update(
        doi='10.80507/dandi.000000', metadata={**version.metadata, 'doi': '10.80507/dandi.000000'}
    )
    version.refresh_from_db()

    assert missing_manifest_dois(version) == {
        _dandiset_jsonld_path(version): f'DOI {old_doi}',
        _dandiset_yaml_path(version): f'DOI {old_doi}',
    }


# Case 3: a DOI on the version row which is missing from its metadata.


@pytest.mark.django_db
def test_audit_version_detects_metadata_missing_doi():
    version: Version = PublishedVersionFactory.create()
    write_manifest_files(version.id)
    _strip_metadata_doi(version)

    audit = audit_version(version)
    assert audit.metadata_missing_doi
    assert not audit.model_missing_doi
    assert not audit.missing_manifests
    # Without a DOI in the metadata there's nothing to hold the manifests to.
    assert audit.manifests_missing_doi == {}


# Case 4: no DOI on the version row.


@pytest.mark.django_db
def test_audit_version_detects_model_missing_doi():
    version: Version = PublishedVersionFactory.create(doi=None)
    write_manifest_files(version.id)

    audit = audit_version(version)
    assert audit.model_missing_doi
    assert not audit.metadata_missing_doi
    assert not audit.missing_manifests
    assert audit.manifests_missing_doi == {}


@pytest.mark.django_db
def test_audit_version_reports_a_clean_version():
    version: Version = PublishedVersionFactory.create()
    write_manifest_files(version.id)

    assert not audit_version(version).has_problems


# The commands, which report what the checks above find and optionally rewrite it.


@pytest.mark.django_db
@pytest.mark.parametrize('subcommand', ['report', 'missing-manifest-dois'])
def test_reporting_writes_nothing(version_with_doi_less_manifests, subcommand: str):
    """Reporting is read-only, so a run without --rewrite-manifests is a dry run of it."""
    audit_manifests_and_dois(subcommand, '--all')

    assert missing_manifest_dois(version_with_doi_less_manifests) != {}


@pytest.mark.django_db
def test_missing_manifests_rewrites_only_the_missing_manifests(version_with_doi_less_manifests):
    """Case 1 writes the manifests absent from storage, and leaves case 2 to its subcommand."""
    version: Version = PublishedVersionFactory.create()
    write_manifest_files(version.id)
    default_storage.delete(_assets_yaml_path(version))

    audit_manifests_and_dois('missing-manifests', '--all', '--rewrite-manifests')

    assert missing_manifest_paths(version) == []
    assert missing_manifest_dois(version_with_doi_less_manifests) != {}


@pytest.mark.django_db
def test_missing_manifest_dois_rewrites_only_the_dandiset_manifests(
    version_with_doi_less_manifests,
):
    """Case 2 writes the two manifests which embed the DOI, and nothing else."""
    version = version_with_doi_less_manifests
    untouchable = [
        _assets_jsonld_path(version),
        _assets_yaml_path(version),
        _collection_jsonld_path(version),
    ]
    # The audit never reads these, so sentinels in place of their contents survive unless the
    # repair rewrites manifests it wasn't asked to.
    for path in untouchable:
        default_storage.save(path, ContentFile(b'sentinel'))

    audit_manifests_and_dois('missing-manifest-dois', '--all', '--rewrite-manifests')

    dandiset_jsonld, dandiset_yaml = _written_manifests(version)
    assert dandiset_jsonld['doi'] == version.doi
    assert dandiset_yaml['doi'] == version.doi
    assert version.doi in dandiset_jsonld['citation']
    for path in untouchable:
        with default_storage.open(path) as f:
            assert f.read() == b'sentinel'


@pytest.mark.django_db
def test_rewriting_leaves_the_published_version_untouched(version_with_doi_less_manifests):
    """Published versions are immutable; only the manifest files may be rewritten."""
    version = version_with_doi_less_manifests
    original_fields = model_to_dict(version)
    original_modified = version.modified

    audit_manifests_and_dois('missing-manifest-dois', '--all', '--rewrite-manifests')

    version.refresh_from_db()
    assert model_to_dict(version) == original_fields
    assert version.modified == original_modified


@pytest.mark.django_db
def test_rewriting_cannot_repair_a_metadata_missing_its_doi():
    """A DOI absent from the metadata can't be written into a manifest, so none is rewritten.

    Rewriting from DOI-less metadata would strip the DOI the manifests already carry.
    """
    version: Version = PublishedVersionFactory.create()
    write_manifest_files(version.id)
    _strip_metadata_doi(version)

    audit_manifests_and_dois('missing-manifest-dois', '--all', '--rewrite-manifests')

    version.refresh_from_db()
    assert 'doi' not in version.metadata
    dandiset_jsonld, dandiset_yaml = _written_manifests(version)
    assert dandiset_jsonld['doi'] == version.doi
    assert dandiset_yaml['doi'] == version.doi


@pytest.mark.django_db
def test_drafts_are_never_audited(draft_version: Version):
    """Drafts never have a DOI, and their manifests are rewritten whenever they're modified."""
    assert draft_version not in _version_queryset((), include_all=True)
