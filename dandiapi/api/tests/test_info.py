from django.conf import settings

from dandiapi.api.views.info import schema_url
from dandiapi import __version__


def test_rest_info(api_client):
    resp = api_client.get('/api/info/')
    assert resp.status_code == 200
    assert resp.json() == {
        'schema_version': settings.DANDI_SCHEMA_VERSION,
        'schema_url': schema_url,
        'version': __version__.lstrip('v'),
        'cli-minimal-version': '0.14.2',
        'cli-bad-versions': [],
        'services': {
            'api': {'url': f'{settings.DANDI_API_URL}/api/'},
            'webui': {'url': settings.DANDI_WEB_APP_URL},
            'jupyterhub': {'url': settings.DANDI_JUPYTERHUB_URL},
        },
    }
