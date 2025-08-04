from __future__ import annotations

from typing import Literal, get_args

from django.db import models

AuditRecordType = Literal[
    'create_dandiset',
    'change_owners',
    'update_metadata',
    'add_asset',
    'update_asset',
    'remove_asset',
    'create_zarr',
    'upload_zarr_chunks',
    'delete_zarr_chunks',
    'finalize_zarr',
    'unembargo_dandiset',
    'publish_dandiset',
    'delete_dandiset',
]
AUDIT_RECORD_CHOICES = [(t, t) for t in get_args(AuditRecordType)]


class AuditRecord(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    dandiset_id = models.IntegerField()

    # GitHub enforces a 39 character limit on usernames (see, e.g.,
    # https://docs.github.com/en/enterprise-cloud@latest/admin/managing-iam/iam-configuration-reference/username-considerations-for-external-authentication).
    username = models.CharField(max_length=39)

    # According to RFC 5321 (https://www.rfc-editor.org/rfc/rfc5321.txt),
    # section 4.5.3.1.3, an email address "path" is limited to 256 octets,
    # including the surrounding angle brackets. Without the brackets, that
    # leaves 254 characters for the email address itself.
    user_email = models.CharField(max_length=254)

    # The signup questionnaire imposes a 150 character limit on both first and
    # last names; together with a space to separate them, that makes a 301
    # character limit on the full name.
    user_fullname = models.CharField(max_length=301)
    record_type = models.CharField(max_length=32, choices=AUDIT_RECORD_CHOICES)
    details = models.JSONField(blank=True)

    # These fields are only used when these audit actions are done by admins
    admin = models.BooleanField(default=False)
    description = models.TextField(null=False, default='')

    class Meta:
        constraints = [
            # Require a description for admin-executed actions.
            models.CheckConstraint(
                name='admin-description-pairing',
                check=(
                    models.Q(admin=False, description='')
                    | (models.Q(admin=True) & ~models.Q(description=''))
                ),
            )
        ]

    def __str__(self):
        return f'{self.record_type}/{self.dandiset_id:06}'
