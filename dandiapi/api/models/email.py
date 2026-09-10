from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.db import models
from django_extensions.db.models import TimeStampedModel

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dandiapi.api.models.dandiset import Dandiset


class EmailTemplate(TimeStampedModel):
    """
    Stores email template metadata.

    Templates are identified by a unique name (e.g., "publish_reminder", "ownership_added").
    The actual template content is stored in the filesystem at dandiapi/api/templates/api/mail/.
    This model tracks which templates exist and provides metadata for tracking/auditing.
    """

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text='Unique identifier for the template (e.g., "publish_reminder")',
    )
    subject_template = models.CharField(
        max_length=500,
        help_text='Subject line template pattern (for documentation purposes).',
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text='Description of when this template is used.',
    )

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class SentEmail(TimeStampedModel):
    """
    Tracks all emails sent by the system.

    This provides a complete audit trail of email communications, including:
    - What template was used
    - Who received the email
    - What the actual content was
    - When it was sent
    - Related entities (dandiset, user, etc.)
    """

    # Link to the template used (optional - some emails may be sent without templates)
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_emails',
        help_text='The template used to generate this email.',
    )

    # Store template name even if template is deleted for audit purposes
    template_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Name of the template used (preserved if template is deleted).',
    )

    # Email metadata
    subject = models.CharField(
        max_length=500,
        help_text='The actual subject line sent.',
    )
    to = models.JSONField(
        default=list,
        help_text='List of recipient email addresses.',
    )
    cc = models.JSONField(
        default=list,
        blank=True,
        help_text='List of CC recipient email addresses.',
    )
    bcc = models.JSONField(
        default=list,
        blank=True,
        help_text='List of BCC recipient email addresses.',
    )
    reply_to = models.JSONField(
        default=list,
        blank=True,
        help_text='List of reply-to email addresses.',
    )

    # Email content
    text_content = models.TextField(
        help_text='Plain text version of the email.',
    )
    html_content = models.TextField(
        blank=True,
        default='',
        help_text='HTML version of the email.',
    )

    # Context used to render the template (for debugging/audit purposes)
    render_context = models.JSONField(
        default=dict,
        blank=True,
        help_text='The context variables used to render the template.',
    )

    # Related entities (optional - for linking emails to specific objects)
    dandiset = models.ForeignKey(
        'api.Dandiset',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_emails',
        help_text='The dandiset this email relates to (if applicable).',
    )

    # Track which User objects received this email
    # This allows querying "show me all emails sent to this user"
    # Note: Not all recipients are necessarily users (e.g., admin emails)
    recipients = models.ManyToManyField(
        User,
        blank=True,
        related_name='received_emails',
        help_text='User objects who received this email.',
    )

    # Timestamp for when the email was actually sent (may differ from created)
    sent_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the email was sent.',
    )

    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['template_name']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['dandiset']),
        ]

    def __str__(self) -> str:
        recipients = ', '.join(self.to[:3])
        if len(self.to) > 3:
            recipients += f' (+{len(self.to) - 3} more)'
        return f'{self.template_name or "custom"}: {self.subject} -> {recipients}'

    @classmethod
    def record_email(
        cls,
        *,
        subject: str,
        to: list[str],
        text_content: str,
        html_content: str = '',
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        reply_to: list[str] | None = None,
        template_name: str = '',
        render_context: dict | None = None,
        dandiset: Dandiset | None = None,
        recipient_users: Iterable[User] | None = None,
    ) -> SentEmail:
        """
        Record a sent email in the database.

        This should be called after successfully sending an email to maintain
        an audit trail of all email communications.

        Args:
            subject: The email subject line
            to: List of recipient email addresses
            text_content: Plain text version of the email
            html_content: HTML version of the email (optional)
            cc: List of CC email addresses (optional)
            bcc: List of BCC email addresses (optional)
            reply_to: List of reply-to addresses (optional)
            template_name: Name of the template used (e.g., "publish_reminder")
            render_context: Context variables used to render the template
            dandiset: The Dandiset this email relates to (optional)
            recipient_users: User objects who received this email (optional).
                            Use this when recipients are users in the system.
        """
        # Try to find the template by name
        template = None
        if template_name:
            template = EmailTemplate.objects.filter(name=template_name).first()

        sent_email = cls.objects.create(
            template=template,
            template_name=template_name,
            subject=subject,
            to=to,
            cc=cc or [],
            bcc=bcc or [],
            reply_to=reply_to or [],
            text_content=text_content,
            html_content=html_content,
            render_context=render_context or {},
            dandiset=dandiset,
        )

        # Add recipient users if provided
        if recipient_users:
            sent_email.recipients.add(*recipient_users)

        return sent_email
