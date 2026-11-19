from __future__ import annotations

from django.db import models


class AssetPath(models.Model):
    """
    The path of an asset within a version, and the size of that asset.

    Only the paths of assets are stored. The folders containing them, along with the number and
    total size of the assets within each of those folders, are derived from these when needed.
    """

    # Use 'C' collation to ensure that ordering is handled correctly when slashes are involved
    path = models.CharField(max_length=512, db_collation='C')

    # Protect deletion, as an asset can't be deleted while a version still contains it
    asset = models.ForeignKey('Asset', related_name='leaf_paths', on_delete=models.PROTECT)

    # Cascade deletion, as if the entire version is deleted,
    # all paths associated to that version are no longer relevant
    version = models.ForeignKey('Version', related_name='asset_paths', on_delete=models.CASCADE)

    # The size of the asset, as of when it was last added to the version or ingested
    size = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            # Disallow slashes at the beginning or end of path
            models.CheckConstraint(
                condition=~(models.Q(path__endswith='/') | models.Q(path__startswith='/')),
                name='consistent-slash',
            ),
            models.UniqueConstraint(fields=['asset', 'version'], name='unique-asset-version'),
            # The size and asset are included so that the contents of a folder can be
            # derived from this index alone, without needing to read each asset path.
            models.UniqueConstraint(
                fields=['version', 'path'], include=['size', 'asset'], name='unique-version-path'
            ),
        ]

    def __str__(self) -> str:
        return self.path
