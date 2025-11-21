from __future__ import annotations

from dandischema.conf import get_instance_config


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
