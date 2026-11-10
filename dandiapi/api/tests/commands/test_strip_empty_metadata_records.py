from __future__ import annotations

from copy import deepcopy

from django.core.management import call_command
import pytest

from dandiapi.api.models import AuditRecord, Version
from dandiapi.api.tests.factories import DraftVersionFactory, PublishedVersionFactory

ETHICS_APPROVAL = {'schemaKey': 'EthicsApproval', 'identifier': 'IRB-2026-001'}


def _version_with_empty_records(factory, **kwargs) -> Version:
    version = factory.create(**kwargs)
    version.metadata['ethicsApproval'] = [
        {**ETHICS_APPROVAL, 'contactPoint': {'schemaKey': 'ContactPoint'}}
    ]
    version.save()
    return version


@pytest.mark.django_db
def test_strip_empty_metadata_records_check(capsys):
    draft = _version_with_empty_records(DraftVersionFactory)
    metadata = deepcopy(draft.metadata)

    call_command('strip_empty_metadata_records', '--all', '--check')

    out = capsys.readouterr().out
    assert f'--- a/{draft}\n' in out
    assert '-    schemaKey: ContactPoint\n' in out
    draft.refresh_from_db()
    assert draft.metadata == metadata
    assert not AuditRecord.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('status', 'expected_status'),
    [
        (Version.Status.VALID, Version.Status.PENDING),
        # Stays identical to its published version, so must stay unpublishable
        (Version.Status.PUBLISHED, Version.Status.PUBLISHED),
        (Version.Status.PUBLISHING, Version.Status.PUBLISHING),
    ],
)
def test_strip_empty_metadata_records(status, expected_status):
    draft = _version_with_empty_records(DraftVersionFactory, status=status)
    other_draft = _version_with_empty_records(DraftVersionFactory)
    published = _version_with_empty_records(PublishedVersionFactory, dandiset=draft.dandiset)
    untouched = [(v, deepcopy(v.metadata)) for v in (other_draft, published)]

    call_command('strip_empty_metadata_records', str(draft.dandiset.id))

    draft.refresh_from_db()
    assert draft.status == expected_status
    if status == Version.Status.PUBLISHING:
        assert not AuditRecord.objects.exists()
    else:
        assert draft.metadata['ethicsApproval'] == [ETHICS_APPROVAL]
        assert AuditRecord.objects.get().dandiset_id == draft.dandiset_id
    for version, metadata in untouched:
        version.refresh_from_db()
        assert version.metadata == metadata
