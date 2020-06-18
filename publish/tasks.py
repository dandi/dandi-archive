from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.transaction import atomic

from publish.models import Asset, Dandiset, Version
from .girder import GirderClient


logger = get_task_logger(__name__)


@shared_task
@atomic
def publish_version(dandiset_id: int) -> None:
    with GirderClient() as client:
        dandiset = Dandiset.objects.get(pk=dandiset_id)
        version = Version.from_girder(dandiset, client)

        for girder_file in client.files_in_folder(dandiset.draft_folder_id):
            Asset.from_girder(version, girder_file, client)
