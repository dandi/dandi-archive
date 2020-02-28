import re

from girder.models.collection import Collection
from girder.utility import setting_utilities
from girder.exceptions import ValidationException

DANDISET_ID_COUNTER = "dandi.id_counter"
DANDISET_ID_LENGTH = 6
DANDI_STAGING_COLLECTION_NAME = "Dandiset Staging"

dandiset_id_pattern = r"^\d{6}$"


@setting_utilities.validator(DANDISET_ID_COUNTER)
def _validate(doc):
    if len(str(doc["value"])) > DANDISET_ID_LENGTH:
        raise ValidationException("Dandiset ID limit exceeded", "value")


def validate_dandiset_id(dandiset_id):
    return bool(re.match(dandiset_id_pattern, dandiset_id))


def staging_collection():
    return Collection().createCollection(
        DANDI_STAGING_COLLECTION_NAME, reuseExisting=True,
    )
