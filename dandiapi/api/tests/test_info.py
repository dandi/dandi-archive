from __future__ import annotations

from unittest.mock import ANY

from dandischema.conf import get_instance_config
from django.conf import settings

from dandiapi.api.views.info import get_schema_url

from .fuzzy import Re


def test_rest_info_instance_config_include_none(api_client):
    resp = api_client.get('/api/info/')
    assert resp.status_code == 200

    # Ensure that there is no difference in the keys being returned from the info endpoint. If the
    # info endpoint were missing values, it would allow for default values to be creep in when
    # de-serializing the JSON into a Pydantic model.
    assert (
        resp.json()['instance_config'].keys()
        == get_instance_config().model_dump(mode='json', exclude_none=False).keys()
    )


def test_rest_info(api_client):
    resp = api_client.get('/api/info/')
    assert resp.status_code == 200

    # Get the expected schema URL
    schema_url = get_schema_url()

    resp_json = resp.json()

    assert resp_json == {
        'instance_config': ANY,
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
