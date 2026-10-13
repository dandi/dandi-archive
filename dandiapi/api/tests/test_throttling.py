from __future__ import annotations

import faker
import pytest

from dandiapi.api.tests.factories import UserFactory
from dandiapi.api.throttling import DandiAnonRateThrottle

ANON_RATE_LIMIT = 3


@pytest.fixture
def _anon_rate_limit(mocker):
    # DRF binds `THROTTLE_RATES` to the "DEFAULT_THROTTLE_RATES" setting when it's first
    # imported, so overriding the setting itself would have no effect here
    mocker.patch.dict(DandiAnonRateThrottle.THROTTLE_RATES, {'anon': f'{ANON_RATE_LIMIT}/minute'})


@pytest.fixture
def client_ip_address():
    # Anonymous clients are identified by IP address, so use a random address in every test, to
    # isolate each one from the request history that other tests and test runs leave behind in
    # the cache. The `faker` fixture isn't used, as it's seeded identically in every test run.
    return faker.Faker().ipv4()


@pytest.mark.django_db
@pytest.mark.usefixtures('_anon_rate_limit')
def test_throttling_anonymous(api_client, client_ip_address):
    for _ in range(ANON_RATE_LIMIT):
        resp = api_client.get('/api/info/', REMOTE_ADDR=client_ip_address)
        assert resp.status_code == 200

    resp = api_client.get('/api/info/', REMOTE_ADDR=client_ip_address)
    assert resp.status_code == 429


@pytest.mark.django_db
@pytest.mark.usefixtures('_anon_rate_limit')
def test_throttling_authenticated(api_client, client_ip_address):
    api_client.force_authenticate(user=UserFactory.create())

    # Only anonymous requests are rate limited, so the limit shouldn't apply here
    for _ in range(ANON_RATE_LIMIT + 1):
        resp = api_client.get('/api/info/', REMOTE_ADDR=client_ip_address)
        assert resp.status_code == 200
