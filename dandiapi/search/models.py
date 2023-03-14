from django.db import models


class AssetSearch(models.Model):
    asset_id = models.PositiveBigIntegerField(primary_key=True)
    asset_metadata = models.JSONField()
    asset_size = models.PositiveBigIntegerField()

    class Meta:
        managed = False
        db_table = 'asset_search'
