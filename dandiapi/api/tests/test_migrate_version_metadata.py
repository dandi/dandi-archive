from __future__ import annotations

from django.conf import settings
import pytest

from dandiapi.api.management.commands.migrate_version_metadata import (
    migrate_version_metadata,
)
from dandiapi.api.tests.factories import DraftVersionFactory, PublishedVersionFactory


def _set_old_schema_version(version, schema_version='0.6.0'):
    """Helper function to set an older schema version on a version object."""
    version.metadata['schemaVersion'] = schema_version
    version.save()


@pytest.mark.django_db
def test_migrate_version_metadata_all():
    """Test migrating all draft versions to a target schema version."""
    # Create multiple dandisets with draft versions
    version1 = DraftVersionFactory.create()
    version2 = DraftVersionFactory.create()
    version3 = DraftVersionFactory.create()

    # Simulate older schema versions by modifying metadata
    _set_old_schema_version(version1)
    _set_old_schema_version(version2)
    _set_old_schema_version(version3)

    # Get the current schema version from settings
    target_version = settings.DANDI_SCHEMA_VERSION

    # Run the migration command
    migrate_version_metadata('--all', f'--target={target_version}')

    # Refresh from database
    version1.refresh_from_db()
    version2.refresh_from_db()
    version3.refresh_from_db()

    # Verify that the schema version was set correctly
    assert version1.metadata['schemaVersion'] == target_version
    assert version2.metadata['schemaVersion'] == target_version
    assert version3.metadata['schemaVersion'] == target_version

    # Verify that metadata structure is preserved (basic check)
    assert 'schemaKey' in version1.metadata
    assert 'schemaKey' in version2.metadata
    assert 'schemaKey' in version3.metadata


@pytest.mark.django_db
def test_migrate_version_metadata_specific_dandisets():
    """Test migrating specific dandisets by ID."""
    # Create multiple dandisets with draft versions
    version1 = DraftVersionFactory.create()
    version2 = DraftVersionFactory.create()
    version3 = DraftVersionFactory.create()

    # Simulate older schema versions by modifying metadata
    old_schema_version = '0.6.0'
    _set_old_schema_version(version1, old_schema_version)
    _set_old_schema_version(version2, old_schema_version)
    _set_old_schema_version(version3, old_schema_version)

    # Get the current schema version from settings
    target_version = settings.DANDI_SCHEMA_VERSION

    # Run the migration command for specific dandisets
    migrate_version_metadata(
        str(version1.dandiset.id),
        str(version3.dandiset.id),
        f'--target={target_version}',
    )

    # Refresh from database
    version1.refresh_from_db()
    version2.refresh_from_db()
    version3.refresh_from_db()

    # Verify that the schema version was set for selected versions
    assert version1.metadata['schemaVersion'] == target_version
    assert version3.metadata['schemaVersion'] == target_version

    # Version 2 should be unchanged (we didn't migrate it)
    assert version2.metadata['schemaVersion'] == old_schema_version


@pytest.mark.django_db
def test_migrate_version_metadata_error_no_args():
    """Test that command fails when neither dandisets nor --all is specified."""
    target_version = settings.DANDI_SCHEMA_VERSION

    # This should raise an exception
    with pytest.raises(SystemExit):
        migrate_version_metadata(f'--target={target_version}')


@pytest.mark.django_db
def test_migrate_version_metadata_error_both_args():
    """Test that command fails when both dandisets and --all are specified."""
    version = DraftVersionFactory.create()
    target_version = settings.DANDI_SCHEMA_VERSION

    # This should raise an exception
    with pytest.raises(SystemExit):
        migrate_version_metadata(
            str(version.dandiset.id), '--all', f'--target={target_version}'
        )


@pytest.mark.django_db
def test_migrate_version_metadata_error_no_target():
    """Test that command fails when --target is not specified."""
    version = DraftVersionFactory.create()

    # This should raise an exception
    with pytest.raises(SystemExit):
        migrate_version_metadata('--all')


@pytest.mark.django_db
def test_migrate_version_metadata_only_draft_versions():
    """Test that only draft versions are migrated, not published ones."""
    # Create a draft and a published version
    draft_version = DraftVersionFactory.create()
    published_version = PublishedVersionFactory.create()

    # Simulate older schema versions by modifying metadata
    old_schema_version = '0.6.0'
    _set_old_schema_version(draft_version, old_schema_version)
    _set_old_schema_version(published_version, old_schema_version)

    # Store original published metadata
    original_published_schema = published_version.metadata['schemaVersion']

    # Get the current schema version from settings
    target_version = settings.DANDI_SCHEMA_VERSION

    # Run the migration command
    migrate_version_metadata('--all', f'--target={target_version}')

    # Refresh from database
    draft_version.refresh_from_db()
    published_version.refresh_from_db()

    # Verify that the draft version was migrated
    assert draft_version.metadata['schemaVersion'] == target_version

    # Verify that the published version was NOT migrated
    assert published_version.metadata['schemaVersion'] == original_published_schema


@pytest.mark.django_db
def test_migrate_version_metadata_idempotent():
    """Test that running migration twice doesn't cause issues."""
    version = DraftVersionFactory.create()

    # Simulate older schema version
    _set_old_schema_version(version)

    target_version = settings.DANDI_SCHEMA_VERSION

    # Run the migration command twice
    migrate_version_metadata('--all', f'--target={target_version}')
    version.refresh_from_db()
    metadata_after_first = version.metadata.copy()

    migrate_version_metadata('--all', f'--target={target_version}')
    version.refresh_from_db()

    # Metadata should be the same after second run
    assert version.metadata == metadata_after_first
    assert version.metadata['schemaVersion'] == target_version
