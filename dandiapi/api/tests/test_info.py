from __future__ import annotations

from django.conf import settings

from dandiapi.api.views.info import get_schema_url

from .fuzzy import Re


def test_rest_info(api_client):
    resp = api_client.get('/api/info/')
    assert resp.status_code == 200

    # Get the expected schema URL
    schema_url = get_schema_url()

    assert resp.json() == {
        'schema_version': settings.DANDI_SCHEMA_VERSION,
        'schema_url': schema_url,
        # Matches setuptools_scm's versioning scheme "no-guess-dev"
        'version': Re(r'\d+\.\d+\.\d+(\.post1\.dev\d+\+g[0-9a-f]{7,}(\.d\d{8})?)?'),
        'cli-minimal-version': '0.60.0',
        'cli-bad-versions': [],
        'services': {
            'api': {'url': f'{settings.DANDI_API_URL}/api'},
            'webui': {'url': settings.DANDI_WEB_APP_URL},
            'jupyterhub': {'url': settings.DANDI_JUPYTERHUB_URL},
        },
    }
