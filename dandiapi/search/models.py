from django.db import models


class AssetSearch(models.Model):
    dandiset_id = models.PositiveBigIntegerField()
    asset_id = models.PositiveBigIntegerField(primary_key=True)
    asset_metadata = models.JSONField()
    asset_size = models.PositiveBigIntegerField()

    class Meta:
        managed = False
        db_table = 'asset_search'
        constraints = [
            models.UniqueConstraint(
                fields=['dandiset_id', 'asset_id'], name='unique_dandiset_asset'
            )
        ]
