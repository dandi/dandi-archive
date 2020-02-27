import re

from girder.models.collection import Collection
from girder.utility import setting_utilities
from girder.exceptions import ValidationException

DANDI_ID_COUNTER = "dandi.id_counter"
DANDI_ID_LENGTH = 6
DANDI_STAGING_COLLECTION_NAME = "Dandiset Staging"

dandi_id_pattern = r"^\d{6}$"


@setting_utilities.validator(DANDI_ID_COUNTER)
def _validate(doc):
    if len(str(doc["value"])) > DANDI_ID_LENGTH:
        raise ValidationException("Dandiset ID limit exceeded", "value")


def validate_dandi_id(dandi_id):
    return bool(re.match(dandi_id_pattern, dandi_id))


def pad_dandi_id(dandi_id):
    id_str = str(dandi_id)
    length = len(str(id_str))
    remaining = DANDI_ID_LENGTH - length

    return "%s%s" % (remaining * "0", id_str)


def staging_collection():
    doc = Collection().findOne({"name": DANDI_STAGING_COLLECTION_NAME})

    if doc is None:
        doc = Collection().createCollection(DANDI_STAGING_COLLECTION_NAME, public=False)

    return doc
