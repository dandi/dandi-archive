import re

from girder.exceptions import ValidationException, RestException
from girder.models.collection import Collection
from girder.utility import setting_utilities

DANDISET_IDENTIFIER_COUNTER = "dandi.identifier_counter"
DANDISET_IDENTIFIER_LENGTH = 6
DANDI_DRAFTS_COLLECTION_NAME = "drafts"

dandiset_identifier_pattern = r"^\d{6}$"


@setting_utilities.validator(DANDISET_IDENTIFIER_COUNTER)
def _validate(doc):
    if len(str(doc["value"])) > DANDISET_IDENTIFIER_LENGTH:
        raise ValidationException("Dandiset IDENTIFIER limit exceeded", "value")


def validate_dandiset_identifier(dandiset_identifier):
    return bool(re.match(dandiset_identifier_pattern, dandiset_identifier))


def get_or_create_drafts_collection():
    return Collection().createCollection(DANDI_DRAFTS_COLLECTION_NAME, reuseExisting=True)


def dandiset_identifier(func):
    def wrapper(*args, **kwargs):
        identifier = kwargs["identifier"]
        if not identifier:
            raise RestException("identifier must not be empty.")

        if not validate_dandiset_identifier(identifier):
            raise RestException("Invalid Dandiset Identifier")

        return func(*args, **kwargs)

    return wrapper
