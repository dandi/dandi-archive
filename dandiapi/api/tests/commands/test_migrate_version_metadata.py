from __future__ import annotations

import json

from dandischema.consts import DANDI_SCHEMA_VERSION
from django.core.files.storage import default_storage
import pytest

from dandiapi.api.management.commands.migrate_version_metadata import migrate_version_metadata
from dandiapi.api.manifests import _dandiset_jsonld_path
from dandiapi.api.tasks import write_manifest_files


@pytest.mark.django_db
def test_migrate_version_metadata_rewrites_manifests(draft_version):
    draft_version.metadata['schemaVersion'] = '0.6.4'
    draft_version.save()
    write_manifest_files(draft_version.id)

    migrate_version_metadata(str(draft_version.dandiset_id))

    draft_version.refresh_from_db()
    assert draft_version.metadata['schemaVersion'] == DANDI_SCHEMA_VERSION
    with default_storage.open(_dandiset_jsonld_path(draft_version)) as f:
        assert json.load(f) == draft_version.metadata
