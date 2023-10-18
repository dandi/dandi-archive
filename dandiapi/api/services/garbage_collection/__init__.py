from datetime import timedelta

from django.utils import timezone

from dandiapi.api.models import AssetBlob, Upload
from dandiapi.api.storage import DandiMultipartMixin

# Set this to the expiration time of presigned upload URLs
UPLOAD_EXPIRATION_TIME = DandiMultipartMixin._url_expiration

# TODO: should this be a Django setting?
ASSET_BLOB_EXPIRATION_TIME = timedelta(days=7)


def garbage_collect_uploads() -> int:
    return Upload.objects.filter(
        created__lt=timezone.now() - UPLOAD_EXPIRATION_TIME,
    ).delete()[0]


def garbage_collect_asset_blobs() -> int:
    return AssetBlob.objects.filter(
        assets__isnull=True,
        created__lt=timezone.now() - ASSET_BLOB_EXPIRATION_TIME,
    ).delete()[0]
