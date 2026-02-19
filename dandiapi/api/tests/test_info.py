from __future__ import annotations

import importlib.metadata

from dandischema.conf import get_instance_config
from packaging.specifiers import SpecifierSet
import pytest
import requests


@pytest.mark.django_db
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


def test_cli_minimal_version_matches_dandischema(api_client):
    """Test that local dandischema and minimal cli dandischema are compatible."""
    # Get CLI version info from pypi
    minimal_version = api_client.get('/api/info/').json()['cli-minimal-version']
    data = requests.get(f'https://pypi.org/pypi/dandi/{minimal_version}/json').json()

    # Extract the dandischema requirement
    dandischema_requires = [x for x in data['info']['requires_dist'] if x.startswith('dandischema')]
    assert len(dandischema_requires) == 1
    dandischema_version: str = dandischema_requires[0]
    version_range = SpecifierSet(
        dandischema_version.split(';', maxsplit=1)[0].removeprefix('dandischema').strip()
    )

    # Ensure that local dandischema is compatible with the CLI version
    local_version = importlib.metadata.version('dandischema')
    assert version_range.contains(local_version)
