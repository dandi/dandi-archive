from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from rest_framework.test import APIClient


@pytest.mark.django_db
def test_genotype_autocomplete_rest(api_client: APIClient) -> None:
    resp = api_client.get('/api/search/genotypes/')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_species_autocomplete_rest(api_client: APIClient) -> None:
    resp = api_client.get('/api/search/species/')
    assert resp.status_code == 200
