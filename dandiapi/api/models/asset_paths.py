from __future__ import annotations

from django.db import models


class AssetPath(models.Model):
    # Use 'C' collation to ensure that ordering is handled correctly when slashes are involved
    path = models.CharField(max_length=512, db_collation='C')

    # Protect deletion, since otherwise aggregate fields would become out of sync
    asset = models.ForeignKey(
        'Asset', null=True, blank=True, related_name='leaf_paths', on_delete=models.PROTECT
    )

    # Cascade deletion, as if the entire version is deleted,
    # all paths associated to that version are no longer relevant
    version = models.ForeignKey('Version', related_name='asset_paths', on_delete=models.CASCADE)

    # Aggregate fields
    aggregate_files = models.PositiveBigIntegerField(default=0)
    aggregate_size = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            # Disallow slashes at the beginning or end of path
            models.CheckConstraint(
                condition=~(models.Q(path__endswith='/') | models.Q(path__startswith='/')),
                name='consistent-slash',
            ),
            models.UniqueConstraint(fields=['asset', 'version'], name='unique-asset-version'),
            models.UniqueConstraint(fields=['version', 'path'], name='unique-version-path'),
            # Ensure all leaf paths have at most 1 associated file
            models.CheckConstraint(
                condition=(
                    models.Q(asset__isnull=True)
                    | models.Q(asset__isnull=False, aggregate_files__lte=1)
                ),
                name='consistent-leaf-paths',
            ),
        ]

    def __str__(self) -> str:
        return self.path


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

    def __str__(self) -> str:
        return f'{self.parent} -> {self.child}'
