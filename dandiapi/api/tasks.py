from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.transaction import atomic

from dandiapi.api.girder import GirderClient
from dandiapi.api.models import Asset, Dandiset, Version

logger = get_task_logger(__name__)


@shared_task
@atomic
def publish_version(dandiset_id: int) -> None:
    with GirderClient(authenticate=True) as client:
        dandiset = Dandiset.objects.get(pk=dandiset_id)
        with client.dandiset_lock(dandiset.identifier):
            version = Version.from_girder(dandiset, client)

            for girder_file in client.files_in_folder(dandiset.draft_folder_id):
                Asset.from_girder(version, girder_file, client)
