from __future__ import annotations

from copy import deepcopy

from django.core.management import call_command
import pytest

from dandiapi.api.models import AuditRecord, Version
from dandiapi.api.tests.factories import DraftVersionFactory, PublishedVersionFactory

EMPTY_CONTACT_POINT = {'schemaKey': 'ContactPoint'}
ETHICS_APPROVAL = {'schemaKey': 'EthicsApproval', 'identifier': 'IRB-2026-001'}


def _version_with_empty_records(factory, **kwargs) -> Version:
    version = factory.create(**kwargs)
    version.metadata['ethicsApproval'] = [
        {**ETHICS_APPROVAL, 'contactPoint': deepcopy(EMPTY_CONTACT_POINT)}
    ]
    version.save()
    return version


@pytest.mark.django_db
def test_strip_empty_metadata_records_check():
    draft = _version_with_empty_records(DraftVersionFactory)
    metadata = deepcopy(draft.metadata)

    call_command('strip_empty_metadata_records', '--all', '--check')

    draft.refresh_from_db()
    assert draft.metadata == metadata
    assert not AuditRecord.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('status', 'expected_status'),
    [
        (Version.Status.VALID, Version.Status.PENDING),
        (Version.Status.INVALID, Version.Status.PENDING),
        # The draft is not modified compared to its published version, so it must stay
        # unpublishable
        (Version.Status.PUBLISHED, Version.Status.PUBLISHED),
    ],
)
def test_strip_empty_metadata_records_all(status, expected_status):
    draft = _version_with_empty_records(DraftVersionFactory, status=status)
    clean_draft = DraftVersionFactory.create(status=Version.Status.VALID)
    clean_metadata = deepcopy(clean_draft.metadata)
    published = _version_with_empty_records(PublishedVersionFactory, dandiset=draft.dandiset)
    published_metadata = deepcopy(published.metadata)

    call_command('strip_empty_metadata_records', '--all')

    draft.refresh_from_db()
    assert draft.metadata['ethicsApproval'] == [ETHICS_APPROVAL]
    assert draft.status == expected_status

    audit_record = AuditRecord.objects.get()
    assert audit_record.dandiset_id == draft.dandiset_id
    assert audit_record.record_type == 'update_metadata'
    assert audit_record.admin

    # Clean drafts and published versions are not touched
    clean_draft.refresh_from_db()
    assert clean_draft.metadata == clean_metadata
    assert clean_draft.status == Version.Status.VALID
    published.refresh_from_db()
    assert published.metadata == published_metadata


@pytest.mark.django_db
def test_strip_empty_metadata_records_single_dandiset():
    draft = _version_with_empty_records(DraftVersionFactory)
    other_draft = _version_with_empty_records(DraftVersionFactory)
    other_metadata = deepcopy(other_draft.metadata)

    call_command('strip_empty_metadata_records', str(draft.dandiset.id))

    draft.refresh_from_db()
    assert draft.metadata['ethicsApproval'] == [ETHICS_APPROVAL]
    other_draft.refresh_from_db()
    assert other_draft.metadata == other_metadata


@pytest.mark.django_db
def test_strip_empty_metadata_records_skips_publishing():
    draft = _version_with_empty_records(DraftVersionFactory, status=Version.Status.PUBLISHING)
    metadata = deepcopy(draft.metadata)

    call_command('strip_empty_metadata_records', '--all')

    draft.refresh_from_db()
    assert draft.metadata == metadata
    assert draft.status == Version.Status.PUBLISHING
