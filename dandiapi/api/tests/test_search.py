import pytest


@pytest.mark.django_db
def test_search_no_query(api_client):
    assert api_client.get('/api/search/').data == []


@pytest.mark.django_db
def test_search_empty_query(api_client):
    assert api_client.get('/api/search/', {'search': ''}).data == []


@pytest.mark.django_db
def test_search_identifier(api_client, version):
    resp = api_client.get('/api/search/', {'search': version.dandiset.identifier}).data
    assert len(resp) == 1
    assert resp[0]['version'] == version.version
    assert resp[0]['name'] == version.name


@pytest.mark.django_db
def test_search_metadata(api_client, version):
    key = next(iter(version.metadata.metadata))
    resp = api_client.get('/api/search/', {'search': key}).data

    assert len(resp)
    assert any([ver['dandiset']['identifier'] == version.dandiset.identifier for ver in resp])
