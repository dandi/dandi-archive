from __future__ import annotations

from django.db import models

from dandiapi.api.models.asset import Asset
from dandiapi.api.models.version import Version


class AssetPath(models.Model):
    path = models.CharField(max_length=512)

    # TODO: Determine what should be done on delete
    asset = models.ForeignKey(
        Asset, null=True, blank=True, related_name='leaf_paths', on_delete=models.CASCADE
    )
    version = models.ForeignKey(Version, related_name='asset_paths', on_delete=models.CASCADE)

    aggregate_files = models.PositiveBigIntegerField(default=0)
    aggregate_size = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            # Disallow slashses in path
            models.CheckConstraint(check=~models.Q(path__endswith='/'), name='consistent-slash'),
            models.UniqueConstraint(fields=['asset', 'version'], name='unique-asset-version'),
            models.UniqueConstraint(fields=['version', 'path'], name='unique-version-path'),
        ]


class AssetPathRelation(models.Model):
    # Give related name of child_links, because for any entry with parent=node,
    # all links from node.child_links have the form (parent=node, child=child_node)
    parent = models.ForeignKey(AssetPath, related_name='child_links', on_delete=models.CASCADE)

    # Give related name of parent_links, because for any entry with child=node,
    # all links from node.parent_links have the form (parent=parent_node, child=node)
    child = models.ForeignKey(AssetPath, related_name='parent_links', on_delete=models.CASCADE)

    # Relation depth
    depth = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['parent', 'child'], name='unique-relationship'),
        ]
