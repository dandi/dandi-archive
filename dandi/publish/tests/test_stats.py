import pytest


@pytest.mark.django_db
def test_stats_none(api_client):
    assert api_client.get('/api/stats/').data == {
        'draft_count': 0,
        'published_count': 0,
        'user_count': 0,
        'size': 0,
    }


@pytest.mark.django_db
def test_stats_draft_count(api_client, draft_version):
    assert api_client.get('/api/stats/').data == {
        'draft_count': 1,
        'published_count': 0,
        'user_count': 0,
        'size': 0,
    }


@pytest.mark.django_db
def test_stats_published_count(api_client, version):
    assert api_client.get('/api/stats/').data == {
        'draft_count': 1,
        'published_count': 1,
        'user_count': 0,
        'size': 0,
    }


@pytest.mark.django_db
def test_stats_user_count(api_client, user):
    assert api_client.get('/api/stats/').data == {
        'draft_count': 0,
        'published_count': 0,
        'user_count': 1,
        'size': 0,
    }


@pytest.mark.django_db
def test_stats_size(api_client, asset):
    assert api_client.get('/api/stats/').data == {
        'draft_count': 1,
        'published_count': 1,
        'user_count': 0,
        'size': asset.size,
    }
