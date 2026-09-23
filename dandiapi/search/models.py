from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import models
from django.db.models import OuterRef, Q, Subquery
from django.db.models.functions import Upper

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
    species = models.CharField(max_length=255)
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


class OntologyTerm(models.Model):
    """A term from one of the anatomy ontologies the search operators understand."""

    # Canonical CURIE, e.g. `UBERON:0002421` or `MBA:1089`.
    curie = models.CharField(max_length=64, unique=True)
    ontology = models.CharField(max_length=16)
    iri = models.CharField(max_length=512)
    label = models.CharField(max_length=512)
    # Lowercased label and synonyms, for exact case-insensitive lookup.
    names = ArrayField(models.CharField(max_length=512), default=list)

    class Meta:
        indexes = [
            GinIndex(fields=['names'], name='ontologyterm_names_gin'),
            GinIndex(
                OpClass(Upper('label'), name='gin_trgm_ops'),
                name='ontologyterm_label_trgm',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.curie} ({self.label})'


class OntologyClosure(models.Model):
    """
    One row per (ancestor, descendant) pair, including each term paired with itself.

    "Descendant" covers subclasses and parts, and for a UBERON term the
    corresponding regions of the species atlases, so a search on a region is
    one join away from everything inside it.
    See `dandiapi.search.ontology` for how the rows are computed.
    """

    ancestor = models.ForeignKey(
        OntologyTerm, related_name='descendant_links', on_delete=models.CASCADE
    )
    descendant = models.ForeignKey(
        OntologyTerm, related_name='ancestor_links', on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['ancestor', 'descendant'], name='unique_ontology_closure_pair'
            )
        ]

    def __str__(self) -> str:
        return f'{self.ancestor_id} > {self.descendant_id}'
