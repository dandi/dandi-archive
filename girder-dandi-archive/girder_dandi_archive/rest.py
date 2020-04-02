from girder.api import access
from girder.api.describe import autoDescribeRoute, describeRoute, Description
from girder.api.rest import Resource
from girder.constants import TokenScope
from girder.exceptions import RestException
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.user import User

from .util import (
    DANDISET_IDENTIFIER_COUNTER,
    DANDISET_IDENTIFIER_LENGTH,
    get_or_create_drafts_collection,
    validate_dandiset_identifier,
)


class DandiResource(Resource):
    def __init__(self):
        super(DandiResource, self).__init__()

        self.resourceName = "dandi"
        self.route("GET", (":identifier",), self.get_dandiset)
        self.route("GET", (), self.list_dandisets)
        self.route("POST", (), self.create_dandiset)
        self.route("GET", ("stats",), self.stats)

    @access.user(scope=TokenScope.DATA_WRITE)
    @describeRoute(
        Description("Create Dandiset")
        .param("name", "Name of the Dandiset")
        .param("description", "Description of the Dandiset")
    )
    def create_dandiset(self, params):
        if "name" not in params or "description" not in params:
            raise RestException("Name and description required.")

        name, description = params["name"], params["description"]

        if not name or not description:
            raise RestException("Name and description must not be empty.")

        new_identifier_count = Setting().collection.find_one_and_update(
            {"key": DANDISET_IDENTIFIER_COUNTER},
            {"$inc": {"value": 1}},
            projection={"value": True},
        )["value"]
        padded_identifier = f"{new_identifier_count:0{DANDISET_IDENTIFIER_LENGTH}d}"

        meta = {
            "name": name,
            "description": description,
            "identifier": padded_identifier,
        }

        drafts = get_or_create_drafts_collection()
        folder = Folder().createFolder(
            drafts,
            padded_identifier,
            parentType="collection",
            creator=self.getCurrentUser(),
        )
        folder = Folder().setMetadata(folder, {"dandiset": meta})
        return folder

    @access.public
    @describeRoute(
        Description("Get Dandiset").param(
            "identifier", "Dandiset Identifier", paramType="path"
        )
    )
    def get_dandiset(self, identifier, params):

        if not identifier:
            raise RestException("identifier must not be empty.")

        if not validate_dandiset_identifier(identifier):
            raise RestException("Invalid Dandiset Identifier")

        # Ensure we are only looking for drafts collection child folders.
        drafts = get_or_create_drafts_collection()
        doc = Folder().findOne(
            {"parentId": drafts["_id"], "meta.dandiset.identifier": identifier}
        )
        if not doc:
            raise RestException("No such dandiset found.")
        return doc

    @access.public
    @autoDescribeRoute(
        Description("List Dandisets").pagingParams(
            defaultSort="meta.dandiset.identifier"
        )
    )
    def list_dandisets(self, limit, offset, sort):
        # Ensure we are only looking for drafts collection child folders.
        drafts = get_or_create_drafts_collection()
        return Folder().find(
            {"parentId": drafts["_id"]}, limit=limit, offset=offset, sort=sort
        )

    @access.public
    @describeRoute(Description("Global Dandiset Statistics"))
    def stats(self, params):
        drafts = get_or_create_drafts_collection()
        draft_count = Collection().countFolders(drafts)

        # TODO no way to publish
        published_count = 0

        user_count = User().collection.count_documents({})

        # These aggregate queries are not indexable.
        # Here are some benchmarks I generated for this endpoint as is:
        #    0 dandisets  |  0.008207440376281738 seconds
        # 1000 dandisets  |  0.019745850563049318 seconds
        # 2000 dandisets  |  0.030080437660217285 seconds
        # 1000 more dandisets takes about .011 more seconds
        # Here is the same benchmark but with these aggregate queries removed:
        #    0 dandisets  |  0.004081225395202637
        # 1000 dandisets  |  0.008220505714416505
        # 2000 dandisets  |  0.011307811737060547
        # 1000 more dandisets takes about 0.0035 more seconds

        species_count = list(
            Folder().collection.aggregate(
                [
                    {"$unwind": "$meta.dandiset.organism"},
                    {"$group": {"_id": "$meta.dandiset.organism.species"}},
                    {"$group": {"_id": "0", "count": {"$sum": 1}}},
                ]
            )
        )
        if species_count:
            species_count = species_count[0]["count"]
        else:
            species_count = 0

        subject_count = list(
            Folder().collection.aggregate(
                [
                    {
                        "$group": {
                            "_id": "0",
                            "count": {"$sum": "$meta.dandiset.number_of_subjects"},
                        }
                    },
                ]
            )
        )
        if subject_count:
            subject_count = subject_count[0]["count"]
        else:
            subject_count = 0

        cell_count = list(
            Folder().collection.aggregate(
                [
                    {
                        "$group": {
                            "_id": "0",
                            "count": {"$sum": "$meta.dandiset.number_of_cells"},
                        }
                    },
                ]
            )
        )
        if cell_count:
            cell_count = cell_count[0]["count"]
        else:
            cell_count = 0

        return {
            "draft_count": draft_count,
            "published_count": published_count,
            "user_count": user_count,
            "species_count": species_count,
            "subject_count": subject_count,
            "cell_count": cell_count,
            "size": drafts["size"],
        }
