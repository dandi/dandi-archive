import pytest

from girder.plugin import loadedPlugins


@pytest.mark.plugin("dandi_archive")
def test_import(server):
    assert "dandi_archive" in loadedPlugins()
