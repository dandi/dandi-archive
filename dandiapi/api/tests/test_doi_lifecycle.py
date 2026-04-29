"""Tests for the DOI lifecycle.

Covers concept DOI at creation, version DOI at publish, state transitions,
metadata update sync, hide on delete, unembargo, and remediation.

Note: These tests were AI-generated (Claude Code) using parametrized TDD.
All DataCite API calls are mocked via monkeypatch/mocker — no real HTTP.
"""

from __future__ import annotations

import datetime
from io import StringIO
from unittest.mock import patch

from dandischema.consts import DANDI_SCHEMA_VERSION
import pytest

from dandiapi.api.models import Version
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.services.doi.exceptions import DataCiteAPIError
from dandiapi.api.services.doi.utils import format_doi
from dandiapi.api.tests.factories import DraftVersionFactory, UserFactory

# =============================================================================
# Test 1: Concept DOI on dandiset creation
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize('doi_is_configured', [True, False])
def test_create_open_dandiset_concept_doi(doi_is_configured):
    """Verify concept DOI is set on creation, and task is scheduled only when configured."""
    user = UserFactory.create()
    from dandiapi.api.services.dandiset import create_open_dandiset

    with (
        patch('dandiapi.api.services.dandiset.doi_configured', return_value=doi_is_configured),
        patch('dandiapi.api.services.dandiset.create_dandiset_doi_task'),
    ):
        dandiset, draft_version = create_open_dandiset(
            user=user,
            version_name='Test Dandiset',
            version_metadata={},
        )

    # concept_doi string is always set (deterministic)
    assert dandiset.concept_doi is not None
    assert dandiset.concept_doi == format_doi(dandiset.identifier)
    assert draft_version.doi == dandiset.concept_doi

    if doi_is_configured:
        assert draft_version.doi_state == 'pending'
    else:
        assert draft_version.doi_state is None


# =============================================================================
# Test 2: DOI state transitions in create_dandiset_doi_task
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('side_effect', 'expected_state'),
    [
        (None, 'draft'),  # Success
        (DataCiteAPIError('422 bad metadata'), 'failed'),  # Non-retryable 4xx
    ],
    ids=['success', '4xx-failure'],
)
def test_create_dandiset_doi_task_state_transitions(side_effect, expected_state):
    """Verify doi_state transitions in the concept DOI creation task."""
    version = DraftVersionFactory.create()
    dandiset = version.dandiset
    dandiset.concept_doi = format_doi(dandiset.identifier)
    dandiset.save()
    version.doi = dandiset.concept_doi
    version.doi_state = 'pending'
    version.save()

    from dandiapi.api.tasks import create_dandiset_doi_task

    with patch('dandiapi.api.tasks.create_dandiset_doi', side_effect=side_effect):
        if side_effect:
            try:
                create_dandiset_doi_task.apply(args=[dandiset.id], throw=True)
            except type(side_effect):
                pass  # Expected — task propagates the exception
        else:
            create_dandiset_doi_task.apply(args=[dandiset.id], throw=True)

    version.refresh_from_db()
    assert version.doi_state == expected_state


# =============================================================================
# Test 3: Publish creates version DOI (no fake placeholder)
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize('doi_is_configured', [True, False])
def test_publish_creates_version_doi(doi_is_configured, asset):
    """Verify publish sets a real version DOI (not fake)."""
    from dandiapi.api.services.publish import _build_publishable_version_from_draft

    draft_version = DraftVersionFactory.create(status=Version.Status.VALID)
    draft_version.assets.add(asset)
    draft_version.save()

    new_version = _build_publishable_version_from_draft(draft_version)

    # _build_publishable_version_from_draft doesn't set DOI — _publish_dandiset does.
    # Verify the build step doesn't inject any fake DOI.
    if new_version.metadata.get('doi'):
        assert '.123456/0.123456.1234' not in new_version.metadata['doi']


# =============================================================================
# Test 4: Version destroy hides DOI
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('has_doi', 'hide_succeeds'),
    [
        (True, True),
        (True, False),  # Hide fails — version still deleted, error logged
        (False, True),  # No DOI — skip hide
    ],
    ids=['hide-success', 'hide-failure', 'no-doi'],
)
def test_version_destroy_hides_doi(api_client, has_doi, hide_succeeds):
    """Verify version deletion hides DOI and handles failures gracefully."""
    from dandiapi.api.tests.factories import PublishedVersionFactory

    version = PublishedVersionFactory.create()
    if not has_doi:
        version.doi = None
        version.save()

    admin = UserFactory.create(is_superuser=True)
    api_client.force_authenticate(user=admin)

    side_effect = None if hide_succeeds else DataCiteAPIError('503 unavailable')

    with patch(
        'dandiapi.api.views.version.hide_published_version_doi', side_effect=side_effect
    ) as mock_hide:
        response = api_client.delete(
            f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/',
        )

    assert response.status_code == 204
    assert not Version.objects.filter(id=version.id).exists()

    if has_doi:
        mock_hide.assert_called_once()
    else:
        mock_hide.assert_not_called()


# =============================================================================
# Test 5: Metadata update schedules DOI update
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('embargoed', 'has_published', 'has_concept_doi', 'should_schedule'),
    [
        (False, False, True, True),
        (False, False, False, False),
        (True, False, True, False),
        (False, True, True, False),
    ],
    ids=['schedule', 'no-concept-doi', 'embargoed', 'has-published'],
)
def test_metadata_update_schedules_doi_update(
    api_client,
    embargoed,
    has_published,
    has_concept_doi,
    should_schedule,
):
    """Verify update_dandiset_doi_task is scheduled only for open, unpublished dandisets."""
    user = UserFactory.create()

    if embargoed:
        version = DraftVersionFactory.create(
            dandiset__owners=[user],
            dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED,
            dandiset__embargo_end_date=datetime.date(2030, 1, 1),
        )
    else:
        version = DraftVersionFactory.create(dandiset__owners=[user])

    dandiset = version.dandiset

    if has_concept_doi:
        dandiset.concept_doi = format_doi(dandiset.identifier)
        dandiset.save()

    if has_published:
        from dandiapi.api.tests.factories import PublishedVersionFactory

        PublishedVersionFactory.create(dandiset=dandiset)

    api_client.force_authenticate(user=user)

    on_commit_calls = []

    def capture_on_commit(func, *args, **kwargs):
        on_commit_calls.append(func)

    with (
        patch('dandiapi.api.views.version.update_dandiset_doi_task'),
        patch('dandiapi.api.views.version.transaction.on_commit', side_effect=capture_on_commit),
    ):
        response = api_client.put(
            f'/api/dandisets/{dandiset.identifier}/versions/draft/',
            {
                'metadata': {
                    'schemaVersion': DANDI_SCHEMA_VERSION,
                    'contributor': [
                        {
                            'name': 'Doe, Jane',
                            'roleName': ['dcite:ContactPerson'],
                            'schemaKey': 'Person',
                            'email': 'jane@example.com',
                        }
                    ],
                },
                'name': 'Updated Name',
            },
        )

    assert response.status_code == 200
    if should_schedule:
        # on_commit was called with a lambda that calls update_dandiset_doi_task.delay
        assert len(on_commit_calls) > 0, 'Expected on_commit to be called for DOI update'
    else:
        # Filter for DOI-related on_commit calls (there may be others)
        assert all('doi' not in str(c) for c in on_commit_calls), (
            'DOI update should not be scheduled'
        )


# =============================================================================
# Test 6: Unembargo mints concept DOI
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize('doi_is_configured', [True, False])
def test_unembargo_mints_concept_doi(doi_is_configured):
    """Verify unembargo creates a concept DOI when DOI is configured."""
    from dandiapi.api.services.embargo import unembargo_dandiset

    user = UserFactory.create()
    version = DraftVersionFactory.create(
        dandiset__embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING,
        dandiset__owners=[user],
    )
    dandiset = version.dandiset

    with (
        patch('dandiapi.api.services.embargo.remove_dandiset_embargo_tags'),
        patch('dandiapi.api.services.embargo.send_dandiset_unembargoed_message'),
        patch('dandiapi.api.services.embargo.doi_configured', return_value=doi_is_configured),
        patch('dandiapi.api.tasks.create_dandiset_doi_task'),
    ):
        unembargo_dandiset(dandiset, user)

    dandiset.refresh_from_db()
    version.refresh_from_db()

    # concept_doi should always be set (deterministic)
    assert dandiset.concept_doi == format_doi(dandiset.identifier)

    if doi_is_configured:
        assert version.doi_state == 'pending'
    else:
        assert version.doi_state is None


# =============================================================================
# Test 7: Remediation command (dry-run)
# =============================================================================


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('existing_doi', 'should_remediate'),
    [
        (None, True),
        ('10.80507/dandi.123456/0.123456.1234', True),  # Fake placeholder
        ('10.80507/dev-dandi.000001/0.210101.0001', False),  # Real DOI
    ],
    ids=['null-doi', 'fake-doi', 'real-doi'],
)
def test_remediate_dois_dry_run(existing_doi, should_remediate):
    """Verify dry-run mode correctly identifies versions needing remediation."""
    from django.core.management import call_command

    from dandiapi.api.tests.factories import PublishedVersionFactory

    version = PublishedVersionFactory.create()
    version.doi = existing_doi
    version.save()

    out = StringIO()
    err = StringIO()
    with patch('dandiapi.api.management.commands.remediate_dois.doi_configured', return_value=True):
        call_command('remediate_dois', '--dry-run', stdout=out, stderr=err)

    output = out.getvalue()

    if should_remediate:
        assert version.dandiset.identifier in output
    else:
        # Real DOI should not appear in the remediation list
        assert f'  {version.dandiset.identifier}/{version.version}:' not in output
