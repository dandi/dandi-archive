from __future__ import annotations

from typing import TYPE_CHECKING, Literal, get_args

from django.db import models

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from dandiapi.zarr.models import ZarrArchive

    from .asset import Asset
    from .dandiset import Dandiset

AuditRecordType = Literal[
    'create_dandiset',
    'change_owners',
]
AUDIT_RECORD_CHOICES = [(t, t) for t in get_args(AuditRecordType)]


class AuditRecord(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    dandiset_id = models.IntegerField()
    username = models.CharField(max_length=39)
    user_email = models.CharField(max_length=254)
    user_fullname = models.CharField(max_length=301)
    record_type = models.CharField(max_length=32, choices=AUDIT_RECORD_CHOICES)
    details = models.JSONField(blank=True)

    def __str__(self):
        return f'{self.record_type}/{self.dandiset_id:06}'

    @staticmethod
    def make_audit_record(
        *, dandiset: Dandiset, user: User, record_type: AuditRecordType, details: dict
    ) -> AuditRecord:
        return AuditRecord(
            dandiset_id=dandiset.id,
            username=user.username,
            user_email=user.email,
            user_fullname=f'{user.first_name} {user.last_name}',
            record_type=record_type,
            details=details,
        )

    @staticmethod
    def create_dandiset(*, dandiset: Dandiset, user: User, metadata: dict, embargoed: bool):
        details = {
            'metadata': metadata,
            'embargoed': embargoed,
        }
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='create_dandiset', details=details
        )

    @staticmethod
    def change_owners(
        *, dandiset: Dandiset, user: User, removed_owners: list[User], added_owners: list[User]
    ):
        def glean_user_info(user: User):
            return {
                'username': user.username,
                'email': user.email,
                'name': f'{user.first_name} {user.last_name}',
            }

        details = {
            'removed_owners': [glean_user_info(u) for u in removed_owners],
            'added_owners': [glean_user_info(u) for u in added_owners],
        }
        return AuditRecord.make_audit_record(
            dandiset=dandiset, user=user, record_type='change_owners', details=details
        )
