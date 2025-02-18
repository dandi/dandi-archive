from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.db.models import OuterRef, Q, Subquery

from dandiapi.api.models import Dandiset
from dandiapi.api.services.permissions.dandiset import get_owned_dandisets

if TYPE_CHECKING:
    from django.contrib.auth.models import User


class AssetSearchManager(models.Manager):
    def visible_to(self, user: User) -> models.QuerySet[AssetSearch]:
        """Filter out AssetSearch objects that the user doesn't have permission to view."""
        embargo_statuses_query = Dandiset.objects.filter(id=OuterRef('dandiset_id')).values(
            'embargo_status'
        )
        owned_dandisets_query = get_owned_dandisets(user)

        return self.alias(embargo_status=Subquery(embargo_statuses_query)).filter(
            Q(embargo_status=Dandiset.EmbargoStatus.OPEN) | Q(dandiset_id__in=owned_dandisets_query)
        )


class AssetSearch(models.Model):
    dandiset_id = models.PositiveBigIntegerField()
    asset_id = models.PositiveBigIntegerField(primary_key=True)
    asset_metadata = models.JSONField()
    asset_size = models.PositiveBigIntegerField()

    objects = AssetSearchManager()

    class Meta:
        managed = False
        db_table = 'asset_search'
        constraints = [
            models.UniqueConstraint(
                fields=['dandiset_id', 'asset_id'], name='unique_dandiset_asset'
            )
        ]

    def __str__(self) -> str:
        return f'{self.dandiset_id}:{self.asset_id}'
