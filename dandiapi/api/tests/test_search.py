import pytest


@pytest.mark.django_db
def test_search_no_query(api_client):
    assert api_client.get('/api/search/').data == []


@pytest.mark.django_db
def test_search_empty_query(api_client):
    assert api_client.get('/api/search/', {'search': ''}).data == []


@pytest.mark.django_db
def test_search_identifier(api_client, version):
    resp = api_client.get('/api/search/', {'search': version.id}).data
    assert len(resp) == 1
    assert resp[0]['version'] == version.version
    assert resp[0]['name'] == version.name
