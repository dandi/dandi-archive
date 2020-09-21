from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth.models import User
from django.db.transaction import atomic

from dandiapi.api.girder import GirderClient
from dandiapi.api.models import Asset, Dandiset, Version

logger = get_task_logger(__name__)


@shared_task
@atomic
def publish_version(dandiset_id: int, user_id) -> None:
    dandiset = Dandiset.objects.get(pk=dandiset_id)
    try:
        with GirderClient(authenticate=True) as client:
            with client.dandiset_lock(dandiset.identifier):
                version = Version.from_girder(dandiset, client)

                for girder_file in client.files_in_folder(dandiset.draft_folder_id):
                    Asset.from_girder(version, girder_file, client)
    finally:
        # The draft was locked in django by the publish action
        # We need to unlock it now
        dandiset.draft_version.unlock(User.objects.get(id=user_id))
        dandiset.draft_version.save()
