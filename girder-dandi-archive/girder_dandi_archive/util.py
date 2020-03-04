import re

from girder.models.collection import Collection
from girder.utility import setting_utilities
from girder.exceptions import ValidationException

DANDISET_IDENTIFIER_COUNTER = "dandi.identifier_counter"
DANDISET_IDENTIFIER_LENGTH = 6
DANDI_STAGING_COLLECTION_NAME = "Dandiset Staging"

dandiset_identifier_pattern = r"^\d{6}$"


@setting_utilities.validator(DANDISET_IDENTIFIER_COUNTER)
def _validate(doc):
    if len(str(doc["value"])) > DANDISET_IDENTIFIER_LENGTH:
        raise ValidationException("Dandiset IDENTIFIER limit exceeded", "value")


def validate_dandiset_identifier(dandiset_identifier):
    return bool(re.match(dandiset_identifier_pattern, dandiset_identifier))


def create_staging_collection():
    return Collection().createCollection(
        DANDI_STAGING_COLLECTION_NAME, reuseExisting=True
    )
