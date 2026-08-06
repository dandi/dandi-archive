from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from dandiapi.api.mail import build_publish_reminder_message, send_publish_reminder_message
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.models.email import SentEmail
from dandiapi.api.tasks.scheduled import PUBLISH_REMINDER_DAYS, send_publish_reminder_emails
from dandiapi.api.tests.factories import (
    DandisetFactory,
    DraftVersionFactory,
    PublishedVersionFactory,
    UserFactory,
)


@pytest.mark.django_db
def test_build_publish_reminder_message():
    """Test that the publish reminder message is built correctly."""
    user = UserFactory.create()
    draft_version = DraftVersionFactory.create(dandiset__owners=[user])
    dandiset = draft_version.dandiset

    message = build_publish_reminder_message(dandiset)

    assert message.subject == f'Reminder: Publish your Dandiset "{draft_version.name}"'
    assert user.email in message.to
    assert dandiset.identifier in message.body
    assert 'publish' in message.body.lower()


@pytest.mark.django_db
def test_send_publish_reminder_message(mailoutbox):
    """Test that the publish reminder email is sent correctly and recorded."""
    users = [UserFactory.create() for _ in range(3)]
    draft_version = DraftVersionFactory.create(dandiset__owners=users)
    dandiset = draft_version.dandiset

    sent_email = send_publish_reminder_message(dandiset)

    # Check the email was sent
    assert len(mailoutbox) == 1
    assert 'Reminder' in mailoutbox[0].subject
    assert dandiset.identifier in mailoutbox[0].body

    # Check that all owners received the email
    owner_emails = {user.email for user in users}
    mailbox_to_emails = set(mailoutbox[0].to)
    assert owner_emails == mailbox_to_emails

    # Check the email was recorded in SentEmail
    assert sent_email is not None
    assert sent_email.template_name == 'publish_reminder'
    assert sent_email.dandiset == dandiset
    assert set(sent_email.to) == owner_emails
    assert sent_email.recipients.count() == 3
    assert set(sent_email.recipients.all()) == set(users)


@pytest.mark.django_db
def test_send_publish_reminder_emails_finds_stale_dandisets(mailoutbox):
    """Test that the scheduled task finds stale draft-only dandisets."""
    user = UserFactory.create()

    # Create a stale draft-only dandiset (older than PUBLISH_REMINDER_DAYS)
    stale_draft_version = DraftVersionFactory.create(dandiset__owners=[user])
    stale_draft_version.modified = timezone.now() - timedelta(days=PUBLISH_REMINDER_DAYS + 1)
    stale_draft_version.save(update_fields=['modified'])

    send_publish_reminder_emails()

    assert len(mailoutbox) == 1
    assert stale_draft_version.dandiset.identifier in mailoutbox[0].body


@pytest.mark.django_db
def test_send_publish_reminder_emails_excludes_recent_dandisets(mailoutbox):
    """Test that the scheduled task excludes recently modified dandisets."""
    user = UserFactory.create()

    # Create a recent draft-only dandiset (newer than PUBLISH_REMINDER_DAYS)
    recent_draft_version = DraftVersionFactory.create(dandiset__owners=[user])
    recent_draft_version.modified = timezone.now() - timedelta(days=PUBLISH_REMINDER_DAYS - 1)
    recent_draft_version.save(update_fields=['modified'])

    send_publish_reminder_emails()

    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_send_publish_reminder_emails_excludes_published_dandisets(mailoutbox):
    """Test that the scheduled task excludes dandisets that have been published."""
    user = UserFactory.create()

    # Create a dandiset with a published version
    dandiset = DandisetFactory.create(owners=[user])
    draft_version = DraftVersionFactory.create(dandiset=dandiset)
    draft_version.modified = timezone.now() - timedelta(days=PUBLISH_REMINDER_DAYS + 1)
    draft_version.save(update_fields=['modified'])

    # Add a published version
    PublishedVersionFactory.create(dandiset=dandiset)

    send_publish_reminder_emails()

    # No email should be sent since the dandiset has been published
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_send_publish_reminder_emails_excludes_embargoed_dandisets(mailoutbox):
    """Test that the scheduled task excludes embargoed dandisets."""
    user = UserFactory.create()

    # Create an embargoed dandiset
    dandiset = DandisetFactory.create(
        owners=[user], embargo_status=Dandiset.EmbargoStatus.EMBARGOED
    )
    draft_version = DraftVersionFactory.create(dandiset=dandiset)
    draft_version.modified = timezone.now() - timedelta(days=PUBLISH_REMINDER_DAYS + 1)
    draft_version.save(update_fields=['modified'])

    send_publish_reminder_emails()

    # No email should be sent since the dandiset is embargoed
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_send_publish_reminder_emails_multiple_dandisets(mailoutbox):
    """Test that the scheduled task sends emails to multiple stale dandisets."""
    users = [UserFactory.create() for _ in range(3)]

    # Create multiple stale draft-only dandisets
    stale_versions = []
    for i, user in enumerate(users):
        draft_version = DraftVersionFactory.create(dandiset__owners=[user])
        draft_version.modified = timezone.now() - timedelta(days=PUBLISH_REMINDER_DAYS + i + 1)
        draft_version.save(update_fields=['modified'])
        stale_versions.append(draft_version)

    send_publish_reminder_emails()

    # All stale dandisets should receive emails
    assert len(mailoutbox) == 3

    # Check that each dandiset identifier is in one of the emails
    all_email_bodies = ' '.join(email.body for email in mailoutbox)
    for version in stale_versions:
        assert version.dandiset.identifier in all_email_bodies


@pytest.mark.django_db
def test_send_publish_reminder_emails_mixed_dandisets(mailoutbox):
    """Test that the scheduled task correctly filters a mix of dandisets."""
    user = UserFactory.create()

    # Create a stale draft-only dandiset (should receive email)
    stale_draft = DraftVersionFactory.create(dandiset__owners=[user])
    stale_draft.modified = timezone.now() - timedelta(days=PUBLISH_REMINDER_DAYS + 1)
    stale_draft.save(update_fields=['modified'])

    # Create a recent draft-only dandiset (should NOT receive email)
    recent_draft = DraftVersionFactory.create(dandiset__owners=[user])
    recent_draft.modified = timezone.now() - timedelta(days=PUBLISH_REMINDER_DAYS - 1)
    recent_draft.save(update_fields=['modified'])

    # Create a stale published dandiset (should NOT receive email)
    published_dandiset = DandisetFactory.create(owners=[user])
    stale_published_draft = DraftVersionFactory.create(dandiset=published_dandiset)
    stale_published_draft.modified = timezone.now() - timedelta(days=PUBLISH_REMINDER_DAYS + 1)
    stale_published_draft.save(update_fields=['modified'])
    PublishedVersionFactory.create(dandiset=published_dandiset)

    # Create a stale embargoed dandiset (should NOT receive email)
    embargoed_dandiset = DandisetFactory.create(
        owners=[user], embargo_status=Dandiset.EmbargoStatus.EMBARGOED
    )
    stale_embargoed_draft = DraftVersionFactory.create(dandiset=embargoed_dandiset)
    stale_embargoed_draft.modified = timezone.now() - timedelta(days=PUBLISH_REMINDER_DAYS + 1)
    stale_embargoed_draft.save(update_fields=['modified'])

    send_publish_reminder_emails()

    # Only the stale draft-only dandiset should receive an email
    assert len(mailoutbox) == 1
    assert stale_draft.dandiset.identifier in mailoutbox[0].body
    assert recent_draft.dandiset.identifier not in mailoutbox[0].body
    assert published_dandiset.identifier not in mailoutbox[0].body
    assert embargoed_dandiset.identifier not in mailoutbox[0].body


@pytest.mark.django_db
def test_send_publish_reminder_emails_only_once(mailoutbox):
    """Test that publish reminder emails are only sent once per dandiset."""
    user = UserFactory.create()

    # Create a stale draft-only dandiset
    stale_draft_version = DraftVersionFactory.create(dandiset__owners=[user])
    stale_draft_version.modified = timezone.now() - timedelta(days=PUBLISH_REMINDER_DAYS + 1)
    stale_draft_version.save(update_fields=['modified'])
    dandiset = stale_draft_version.dandiset

    # First run should send an email
    send_publish_reminder_emails()
    assert len(mailoutbox) == 1
    assert dandiset.identifier in mailoutbox[0].body

    # Verify a SentEmail record was created
    sent_emails = SentEmail.objects.filter(
        template_name='publish_reminder',
        dandiset=dandiset,
    )
    assert sent_emails.count() == 1

    # Second run should NOT send another email
    send_publish_reminder_emails()
    assert len(mailoutbox) == 1  # Still only 1 email total

    # Still only one SentEmail record
    assert sent_emails.count() == 1


@pytest.mark.django_db
def test_send_publish_reminder_emails_excludes_already_reminded(mailoutbox):
    """Test that dandisets that have already been reminded are excluded."""
    user = UserFactory.create()

    # Create a stale draft-only dandiset that has already been reminded
    stale_draft_version = DraftVersionFactory.create(dandiset__owners=[user])
    stale_draft_version.modified = timezone.now() - timedelta(days=PUBLISH_REMINDER_DAYS + 1)
    stale_draft_version.save(update_fields=['modified'])

    dandiset = stale_draft_version.dandiset

    # Create a SentEmail record to simulate a previous reminder
    SentEmail.objects.create(
        template_name='publish_reminder',
        subject=f'Reminder: Publish your Dandiset "{stale_draft_version.name}"',
        to=[user.email],
        text_content='Previous reminder content',
        dandiset=dandiset,
    )

    send_publish_reminder_emails()

    # No email should be sent since the dandiset was already reminded
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_send_publish_reminder_emails_records_sent_email(mailoutbox):
    """Test that a SentEmail record is created after sending an email."""
    user = UserFactory.create()

    # Create a stale draft-only dandiset
    stale_draft_version = DraftVersionFactory.create(dandiset__owners=[user])
    stale_draft_version.modified = timezone.now() - timedelta(days=PUBLISH_REMINDER_DAYS + 1)
    stale_draft_version.save(update_fields=['modified'])
    dandiset = stale_draft_version.dandiset

    # Verify no SentEmail records exist initially
    assert SentEmail.objects.filter(dandiset=dandiset).count() == 0

    before_send = timezone.now()
    send_publish_reminder_emails()
    after_send = timezone.now()

    # Verify a SentEmail record was created
    sent_emails = SentEmail.objects.filter(
        template_name='publish_reminder',
        dandiset=dandiset,
    )
    assert sent_emails.count() == 1

    sent_email = sent_emails.first()
    assert sent_email.subject == f'Reminder: Publish your Dandiset "{stale_draft_version.name}"'
    assert user.email in sent_email.to
    assert before_send <= sent_email.sent_at <= after_send
    assert sent_email.recipients.filter(id=user.id).exists()
    assert sent_email.render_context.get('dandiset_identifier') == dandiset.identifier
