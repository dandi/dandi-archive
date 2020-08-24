import pytest


@pytest.mark.django_db
def test_stats_none(api_client):
    resp = api_client.get('/api/stats/')
    assert {
        'draft_count': 0,
        'published_count': 0,
        'user_count': 0,
        'species_count': 0,
        'subject_count': 0,
        'cell_count': 0,
        'size': 0,
    } == resp.json()


@pytest.mark.django_db
def test_stats_draft_count(api_client, draft_version_factory):
    draft_version_factory()
    resp = api_client.get('/api/stats/')
    assert {
        'draft_count': 1,
        'published_count': 0,
        'user_count': 0,
        'species_count': 0,
        'subject_count': 0,
        'cell_count': 0,
        'size': 0,
    } == resp.json()


@pytest.mark.django_db
def test_stats_published_count(api_client, version_factory):
    version_factory()
    resp = api_client.get('/api/stats/')
    assert {
        'draft_count': 1,
        'published_count': 1,
        'user_count': 0,
        'species_count': 0,
        'subject_count': 0,
        'cell_count': 0,
        'size': 0,
    } == resp.json()


@pytest.mark.django_db
def test_stats_user_count(api_client, user_factory):
    user_factory()
    resp = api_client.get('/api/stats/')
    assert {
        'draft_count': 0,
        'published_count': 0,
        'user_count': 1,
        'species_count': 0,
        'subject_count': 0,
        'cell_count': 0,
        'size': 0,
    } == resp.json()


@pytest.mark.django_db
def test_stats_size(api_client, asset_factory):
    asset = asset_factory()
    resp = api_client.get('/api/stats/')
    assert {
        'draft_count': 1,
        'published_count': 1,
        'user_count': 0,
        'species_count': 0,
        'subject_count': 0,
        'cell_count': 0,
        'size': asset.size,
    } == resp.json()
