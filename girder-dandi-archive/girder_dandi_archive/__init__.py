from girder import plugin
from girder.utility import search


class GirderPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = 'DANDI Archive'

    def load(self, info):
        search.addSearchMode('dandi', search.getSearchModeHandler('text'))
