from girder.models.collection import Collection

DANDI_ID_COUNTER = "dandi.id_counter"
DANDI_ID_LENGTH = 6
DANDI_STAGING_COLLECTION_NAME = "Dandiset Staging"


def pad_dandi_id(dandi_id):
    id_str = str(dandi_id)
    length = len(str(id_str))
    remaining = DANDI_ID_LENGTH - length

    return "%s%s" % (remaining * "0", id_str)


def staging_collection():
    doc = Collection().findOne({
        "name": DANDI_STAGING_COLLECTION_NAME
    })

    if doc is None:
        doc = Collection().createCollection(DANDI_STAGING_COLLECTION_NAME, public=False)

    return doc
