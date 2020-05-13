import re

from girder.exceptions import ValidationException
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.user import User
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


def find_dandiset_by_identifier(identifier):
    """Use a unique identifier to find a dandiset in the dandiset drafts collection."""
    drafts = get_or_create_drafts_collection()
    return Folder().findOne({"parentId": drafts["_id"], "meta.dandiset.identifier": identifier})


def find_dandiset(query):
    """Search for dandiset within the dandiset drafts collection."""
    drafts = get_or_create_drafts_collection()
    return Folder().find({"parentId": drafts["_id"], **query})


def dandiset_identifier(func):
    """Raise a ValidationException if the passed dandi identifier is invalid."""

    def wrapper(*args, **kwargs):
        identifier = kwargs.get("identifier")
        if not identifier:
            raise ValidationException("identifier must not be empty.")

        if not validate_dandiset_identifier(identifier):
            raise ValidationException("Invalid Dandiset Identifier")

        return func(*args, **kwargs)

    return wrapper


def get_dandiset_owner(identifier):
    dandiset = find_dandiset_by_identifier(identifier)
    if dandiset is None:
        raise ValidationException("Dandiset does not exist.")

    user = User().findOne({"_id": dandiset["creatorId"]})
    return user
