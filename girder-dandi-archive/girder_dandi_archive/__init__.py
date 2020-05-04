# -*- coding: utf-8 -*-
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.plugin import GirderPlugin
from girder.settings import SettingKey
from girder_user_quota.settings import PluginSettings as UserQuotaPluginSettings

from .rest import DandiResource
from .util import DANDISET_IDENTIFIER_COUNTER


class DandiArchivePlugin(GirderPlugin):
    DISPLAY_NAME = "DANDI Archive"

    def load(self, info):
        # Compound index for rest.DandiResource.get_dandiset.
        # Mongo is not guaranteed to use a singular index when executing the query.
        # meta.dandiset.identifier is specified first so that it is available as an
        # index for other queries that might need it.
        Folder().ensureIndex(([("meta.dandiset.identifier", 1), ("parentId", 1)], {}))

        Setting().collection.update(
            {"key": DANDISET_IDENTIFIER_COUNTER}, {"$setOnInsert": {"value": 1}}, upsert=True,
        )
        # Allow the client and netlify to access the girder server
        Setting().set(SettingKey.CORS_ALLOW_ORIGIN, "*")
        Setting().set(SettingKey.USER_DEFAULT_FOLDERS, "none")
        Setting().set(UserQuotaPluginSettings.DEFAULT_USER_QUOTA, 0)

        info["apiRoot"].dandi = DandiResource()
