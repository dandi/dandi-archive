from django.db import transaction
from django.db.models.query import QuerySet

from dandiapi.api.models.asset import Asset


def bulk_recalculate_asset_metadata(*, assets: QuerySet[Asset]):
    with transaction.atomic():
        for asset in assets.iterator():
            # populates metadata
            asset.save()
