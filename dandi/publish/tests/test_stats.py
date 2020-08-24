import pytest


@pytest.mark.django_db
def test_stats_none(api_client):
    resp = api_client.get('/api/stats/')
    assert resp.json() == {
        'draft_count': 0,
        'published_count': 0,
        'user_count': 0,
        'species_count': 0,
        'subject_count': 0,
        'cell_count': 0,
        'size': 0,
    }


@pytest.mark.django_db
def test_stats_draft_count(api_client, draft_version):
    resp = api_client.get('/api/stats/')
    assert resp.json() == {
        'draft_count': 1,
        'published_count': 0,
        'user_count': 0,
        'species_count': 0,
        'subject_count': 0,
        'cell_count': 0,
        'size': 0,
    }


@pytest.mark.django_db
def test_stats_published_count(api_client, version):
    resp = api_client.get('/api/stats/')
    assert resp.json() == {
        'draft_count': 1,
        'published_count': 1,
        'user_count': 0,
        'species_count': 0,
        'subject_count': 0,
        'cell_count': 0,
        'size': 0,
    }


@pytest.mark.django_db
def test_stats_user_count(api_client, user):
    resp = api_client.get('/api/stats/')
    assert resp.json() == {
        'draft_count': 0,
        'published_count': 0,
        'user_count': 1,
        'species_count': 0,
        'subject_count': 0,
        'cell_count': 0,
        'size': 0,
    }


@pytest.mark.django_db
def test_stats_size(api_client, asset):
    resp = api_client.get('/api/stats/')
    assert resp.json() == {
        'draft_count': 1,
        'published_count': 1,
        'user_count': 0,
        'species_count': 0,
        'subject_count': 0,
        'cell_count': 0,
        'size': asset.size,
    }
