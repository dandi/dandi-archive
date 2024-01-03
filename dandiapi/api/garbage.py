from __future__ import annotations
from datetime import timedelta

from django.db.models import Exists, OuterRef
from django.db.models.query import QuerySet
from django.utils import timezone

from dandiapi.api.models import Asset, Version

# How long after the last modification things are eligible for deletion
STALE_TIME_INTERVAL = timedelta(days=7)


def stale_assets() -> QuerySet[Asset]:
    deadline = timezone.now() - STALE_TIME_INTERVAL
    return (
        Asset.objects.annotate(has_version=Exists(Version.objects.filter(assets=OuterRef('id'))))
        .filter(has_version=False)
        .filter(published=False)
        .filter(modified__lt=deadline)
    )
