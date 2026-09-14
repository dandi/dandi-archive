from __future__ import annotations

import json

from django.core.files.storage import default_storage
from django.forms.models import model_to_dict
import djclick as click
import pytest
import yaml

from dandiapi.api.management.commands.rewrite_manifests_missing_doi import (
    rewrite_manifests_missing_doi,
    stale_manifest_paths,
)
from dandiapi.api.manifests import _dandiset_jsonld_path, _dandiset_yaml_path
from dandiapi.api.models import Version
from dandiapi.api.tasks import write_manifest_files
from dandiapi.api.tests.factories import PublishedVersionFactory


def _written_manifests(version: Version) -> tuple[dict, dict]:
    with default_storage.open(_dandiset_jsonld_path(version)) as f:
        dandiset_jsonld = json.load(f)
    with default_storage.open(_dandiset_yaml_path(version)) as f:
        dandiset_yaml = yaml.safe_load(f)

    return dandiset_jsonld, dandiset_yaml


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


@pytest.mark.django_db
def test_stale_manifest_paths_detects_missing_doi(version_with_doi_less_manifests):
    version = version_with_doi_less_manifests

    assert stale_manifest_paths(version) == [
        _dandiset_jsonld_path(version),
        _dandiset_yaml_path(version),
    ]


@pytest.mark.django_db
def test_stale_manifest_paths_ignores_current_manifests():
    version: Version = PublishedVersionFactory.create()
    write_manifest_files(version.id)

    assert stale_manifest_paths(version) == []


@pytest.mark.django_db
def test_stale_manifest_paths_detects_missing_manifests():
    version: Version = PublishedVersionFactory.create()

    # No manifests have been written at all.
    assert stale_manifest_paths(version) == [
        _dandiset_jsonld_path(version),
        _dandiset_yaml_path(version),
    ]


@pytest.mark.django_db
def test_rewrite_manifests_missing_doi(version_with_doi_less_manifests):
    version = version_with_doi_less_manifests

    rewrite_manifests_missing_doi('--all')

    dandiset_jsonld, dandiset_yaml = _written_manifests(version)
    assert dandiset_jsonld['doi'] == version.doi
    assert dandiset_yaml['doi'] == version.doi
    assert version.doi in dandiset_jsonld['citation']
    assert stale_manifest_paths(version) == []


@pytest.mark.django_db
def test_rewrite_manifests_missing_doi_dry_run(version_with_doi_less_manifests):
    version = version_with_doi_less_manifests

    rewrite_manifests_missing_doi('--all', '--dry-run')

    dandiset_jsonld, dandiset_yaml = _written_manifests(version)
    assert 'doi' not in dandiset_jsonld
    assert 'doi' not in dandiset_yaml


@pytest.mark.django_db
def test_rewrite_manifests_missing_doi_leaves_published_version_untouched(
    version_with_doi_less_manifests,
):
    """Published versions are immutable; only the manifest files may be rewritten."""
    version = version_with_doi_less_manifests
    original_fields = model_to_dict(version)
    original_modified = version.modified

    rewrite_manifests_missing_doi('--all')

    version.refresh_from_db()
    assert model_to_dict(version) == original_fields
    assert version.modified == original_modified


@pytest.mark.django_db
def test_rewrite_manifests_missing_doi_skips_versions_with_unpopulated_metadata_doi(
    version_with_doi_less_manifests,
):
    """A DOI absent from the metadata can't be written into the manifest without a re-save."""
    version = version_with_doi_less_manifests

    # Bypass `Version.save` so the row has a DOI its metadata doesn't reflect.
    Version.objects.filter(id=version.id).update(
        metadata={k: v for k, v in version.metadata.items() if k != 'doi'}
    )
    version.refresh_from_db()

    rewrite_manifests_missing_doi('--all')

    # The version is left alone, and so are its manifests.
    version.refresh_from_db()
    assert 'doi' not in version.metadata
    dandiset_jsonld, dandiset_yaml = _written_manifests(version)
    assert 'doi' not in dandiset_jsonld
    assert 'doi' not in dandiset_yaml


@pytest.mark.django_db
def test_rewrite_manifests_missing_doi_skips_versions_without_doi():
    version: Version = PublishedVersionFactory.create(doi=None)
    write_manifest_files(version.id)

    rewrite_manifests_missing_doi('--all')

    dandiset_jsonld, _ = _written_manifests(version)
    assert 'doi' not in dandiset_jsonld


@pytest.mark.django_db
def test_rewrite_manifests_missing_doi_skips_drafts(draft_version: Version):
    write_manifest_files(draft_version.id)

    rewrite_manifests_missing_doi('--all')

    # The draft has no DOI, and must not be picked up as a published version.
    dandiset_jsonld, _ = _written_manifests(draft_version)
    assert 'doi' not in dandiset_jsonld


@pytest.mark.django_db
def test_rewrite_manifests_missing_doi_filters_by_dandiset(version_with_doi_less_manifests):
    version = version_with_doi_less_manifests
    other_version: Version = PublishedVersionFactory.create()

    rewrite_manifests_missing_doi(str(other_version.dandiset.id))

    # Only the requested dandiset was considered.
    assert stale_manifest_paths(version) != []


@pytest.mark.django_db
def test_rewrite_manifests_missing_doi_requires_a_target():
    with pytest.raises(
        click.ClickException, match="Must specify exactly one of 'dandisets' or --all"
    ):
        rewrite_manifests_missing_doi()
