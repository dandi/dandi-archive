import pytest


@pytest.mark.django_db
def test_stats_baseline(api_client):
    assert api_client.get('/api/stats/').data == {
        'draft_count': 0,
        'published_count': 0,
        'user_count': 0,
        'size': 0,
    }


@pytest.mark.django_db
def test_stats_draft(api_client, draft_version):
    stats = api_client.get('/api/stats/').data

    assert stats['draft_count'] == 1
    assert stats['published_count'] == 0


@pytest.mark.django_db
def test_stats_published(api_client, version):
    stats = api_client.get('/api/stats/').data

    assert stats['draft_count'] == 1
    assert stats['published_count'] == 1


@pytest.mark.django_db
def test_stats_user(api_client, user):
    stats = api_client.get('/api/stats/').data

    assert stats['user_count'] == 1


@pytest.mark.django_db
def test_stats_asset(api_client, asset):
    stats = api_client.get('/api/stats/').data

    assert stats['size'] == asset.size
