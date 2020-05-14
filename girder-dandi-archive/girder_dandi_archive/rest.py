import re

from girder.api import access
from girder.api.describe import autoDescribeRoute, describeRoute, Description
from girder.api.rest import Resource
from girder.constants import AccessType, TokenScope
from girder.exceptions import RestException, ValidationException
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.user import User

from .util import (
    dandiset_identifier,
    DANDISET_IDENTIFIER_COUNTER,
    DANDISET_IDENTIFIER_LENGTH,
    find_dandiset_by_identifier,
    get_dandiset_owners,
    get_or_create_drafts_collection,
    validate_user,
)


class DandiResource(Resource):
    def __init__(self):
        super(DandiResource, self).__init__()

        self.resourceName = "dandi"
        self.route("GET", (":identifier",), self.get_dandiset)
        self.route("GET", (":identifier", "owners"), self.get_dandiset_owners)
        self.route("PUT", (":identifier", "owners"), self.add_dandiset_owners)
        self.route("DELETE", (":identifier", "owners"), self.remove_dandiset_owners)
        self.route("GET", ("user",), self.get_user_dandisets)
        self.route("GET", ("search",), self.search_dandisets)
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
            drafts, padded_identifier, parentType="collection", creator=self.getCurrentUser(),
        )
        folder = Folder().setMetadata(folder, {"dandiset": meta})
        return folder

    @access.public
    @describeRoute(
        Description("Get Dandiset").param("identifier", "Dandiset Identifier", paramType="path")
    )
    @dandiset_identifier
    def get_dandiset(self, identifier, params):
        # Ensure we are only looking for drafts collection child folders.
        drafts = get_or_create_drafts_collection()
        doc = Folder().findOne({"parentId": drafts["_id"], "meta.dandiset.identifier": identifier})
        if not doc:
            raise RestException("No such dandiset found.")
        return doc

    @access.public
    @describeRoute(
        Description("Get Dandiset Owners").param(
            "identifier", "Dandiset Identifier", paramType="path"
        )
    )
    @dandiset_identifier
    def get_dandiset_owners(self, identifier, params):
        return get_dandiset_owners(find_dandiset_by_identifier(identifier))

    @access.user
    @autoDescribeRoute(
        Description("Add Dandiset Owners")
        .param("identifier", "Dandiset Identifier", paramType="path")
        .jsonParam(
            "owners",
            "A JSON list of girder users to add as owners.",
            paramType="body",
            requireArray=True,
        )
    )
    @dandiset_identifier
    def add_dandiset_owners(self, identifier, owners, params):
        dandiset = find_dandiset_by_identifier(identifier)
        Folder().requireAccess(dandiset, user=self.getCurrentUser(), level=AccessType.ADMIN)

        # Make sure the list doesn't contain duplicates
        # Only work with admin level users, removing non-admins from the ACL
        user_id_to_level = {
            str(user["id"]): user["level"]
            for user in Folder().getFullAccessList(dandiset)["users"]
            if user["level"] == AccessType.ADMIN
        }

        for owner in owners:
            if not validate_user(owner):
                raise ValidationException("All owners must be valid user objects.")

            user_id_to_level[owner["_id"]] = AccessType.ADMIN

        final_users = [
            {"id": user_id, "level": level} for user_id, level in user_id_to_level.items()
        ]

        # Assumes there is at least one admin
        admin = next(User().getAdmins())
        doc = Folder().setAccessList(
            dandiset, {"users": final_users}, save=True, recurse=True, user=admin
        )
        return get_dandiset_owners(doc)

    @access.user
    @autoDescribeRoute(
        Description("Remove Dandiset Owners")
        .param("identifier", "Dandiset Identifier", paramType="path")
        .jsonParam(
            "owners",
            "A JSON list of girder users to remove from owners.",
            paramType="body",
            requireArray=True,
        )
    )
    @dandiset_identifier
    def remove_dandiset_owners(self, identifier, owners, params):
        dandiset = find_dandiset_by_identifier(identifier)
        Folder().requireAccess(dandiset, user=self.getCurrentUser(), level=AccessType.ADMIN)

        # Only work with admin level users, removing non-admins from the ACL
        user_id_to_level = {
            str(user["id"]): user["level"]
            for user in Folder().getFullAccessList(dandiset)["users"]
            if user["level"] == AccessType.ADMIN
        }

        for owner in owners:
            if not validate_user(owner):
                raise ValidationException("All owners must be valid user objects.")

            # Prevents a KeyError if owner isn't an existing owner
            user_id_to_level.pop(owner["_id"], None)

        final_users = [
            {"id": user_id, "level": level} for user_id, level in user_id_to_level.items()
        ]

        # Assumes there is at least one admin
        admin = next(User().getAdmins())
        doc = Folder().setAccessList(
            dandiset, {"users": final_users}, save=True, recurse=True, user=admin
        )
        return get_dandiset_owners(doc)

    @access.user
    @autoDescribeRoute(
        Description("Get User Dandisets").pagingParams(defaultSort="meta.dandiset.identifier")
    )
    def get_user_dandisets(self, limit, offset, sort):
        drafts = get_or_create_drafts_collection()
        user_id = self.getCurrentUser()["_id"]

        return Folder().find(
            {"parentId": drafts["_id"], "creatorId": user_id}, limit=limit, offset=offset, sort=sort
        )

    @access.public
    @autoDescribeRoute(
        Description("List Dandisets").pagingParams(defaultSort="meta.dandiset.identifier")
    )
    def list_dandisets(self, limit, offset, sort):
        # Ensure we are only looking for drafts collection child folders.
        drafts = get_or_create_drafts_collection()
        return Folder().find({"parentId": drafts["_id"]}, limit=limit, offset=offset, sort=sort)

    @access.public
    @autoDescribeRoute(
        Description("Search Dandisets")
        .param("search", "Search Query", paramType="query")
        .pagingParams(defaultSort="meta.dandiset.identifier")
    )
    def search_dandisets(self, search, limit, offset, sort):
        # Ensure we are only looking for drafts collection child folders.
        drafts = get_or_create_drafts_collection()
        # TODO Currently only searching identifier, name, description, and contributor name
        # of public dandisets
        if not search:
            # Empty search string should return all possible results
            return Folder().find({"parentId": drafts["_id"]}, limit=limit, offset=offset, sort=sort)
        return Folder().find(
            {
                "parentId": drafts["_id"],
                "$or": [
                    {
                        "meta.dandiset.identifier": {
                            "$regex": re.compile(re.escape(search), re.IGNORECASE)
                        }
                    },
                    {
                        "meta.dandiset.name": {
                            "$regex": re.compile(re.escape(search), re.IGNORECASE)
                        }
                    },
                    {
                        "meta.dandiset.description": {
                            "$regex": re.compile(re.escape(search), re.IGNORECASE)
                        }
                    },
                    {
                        "meta.dandiset.contributors.name": {
                            "$regex": re.compile(re.escape(search), re.IGNORECASE)
                        }
                    },
                ],
            },
            limit=limit,
            offset=offset,
            sort=sort,
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
                [{"$group": {"_id": "0", "count": {"$sum": "$meta.dandiset.number_of_subjects"}}}]
            )
        )
        if subject_count:
            subject_count = subject_count[0]["count"]
        else:
            subject_count = 0

        cell_count = list(
            Folder().collection.aggregate(
                [{"$group": {"_id": "0", "count": {"$sum": "$meta.dandiset.number_of_cells"}}}]
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
