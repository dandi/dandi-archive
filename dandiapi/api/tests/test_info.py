from __future__ import annotations

from unittest.mock import ANY

from dandischema.conf import Config, get_instance_config
from django.conf import settings

from dandiapi import __version__
from dandiapi.api.views.info import get_schema_url


def test_rest_info(api_client):
    instance_config = get_instance_config()

    resp = api_client.get('/api/info/')
    assert resp.status_code == 200

    # Get the expected schema URL
    schema_url = get_schema_url()

    resp_json = resp.json()

    assert resp_json == {
        'instance_config': ANY,
        'schema_version': settings.DANDI_SCHEMA_VERSION,
        'schema_url': schema_url,
        'version': __version__,
        'cli-minimal-version': '0.60.0',
        'cli-bad-versions': [],
        'services': {
            'api': {'url': f'{settings.DANDI_API_URL}/api'},
            'webui': {'url': settings.DANDI_WEB_APP_URL},
            'jupyterhub': {'url': settings.DANDI_JUPYTERHUB_URL},
        },
    }

    # Verify that the instance config can be reconstituted from the info published by the API
    reconstituted_instance_config = Config.model_validate(resp_json['instance_config'])
    assert reconstituted_instance_config == instance_config, (
        "Instance config can't be reconstituted from API response that publishes it"
    )
