from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dandiapi.api.services.search.anatomy import normalize_curie
from dandiapi.api.tests.factories import DandisetFactory, DraftVersionFactory

if TYPE_CHECKING:
    from dandiapi.api.models import Dandiset

pytestmark = pytest.mark.ai_generated

OBO = 'http://purl.obolibrary.org/obo/'
MBAO = 'https://purl.brain-bican.org/ontology/mbao/'


@pytest.mark.parametrize(
    ('identifier', 'expected'),
    [
        ('UBERON:0002421', 'UBERON:0002421'),
        ('uberon:0002421', 'UBERON:0002421'),
        ('UBERON_0002421', 'UBERON:0002421'),
        ('http://purl.obolibrary.org/obo/UBERON_0002421', 'UBERON:0002421'),
        ('https://purl.brain-bican.org/ontology/mbao/MBA_1089', 'MBA:1089'),
        ('https://purl.brain-bican.org/ontology/dhbao/DHBA_10294', 'DHBA:10294'),
        (
            (
                'https://www.ebi.ac.uk/ols4/ontologies/uberon/classes/'
                'http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FUBERON_0002421'
            ),
            'UBERON:0002421',
        ),
        ('http://purl.obolibrary.org/obo/CL_0000598', None),
        ('http://purl.obolibrary.org/obo/NCBITaxon_10090', None),
        ('hippocampus', None),
        ('', None),
        (None, None),
    ],
)
def test_normalize_curie(identifier, expected):
    assert normalize_curie(identifier) == expected


def _seed(*about: dict, schema_key: str = 'Anatomy') -> Dandiset:
    dandiset = DandisetFactory.create()
    version = DraftVersionFactory.create(dandiset=dandiset)
    version.metadata = {
        **version.metadata,
        'about': [{'schemaKey': schema_key, **entry} for entry in about],
    }
    version.save()
    return dandiset


def _search_ids(api_client, query: str) -> set[str]:
    response = api_client.get(
        '/api/dandisets/', {'draft': 'true', 'empty': 'true', 'search': query}
    )
    assert response.status_code == 200, response.json()
    return {r['identifier'] for r in response.json()['results']}


@pytest.fixture
def anatomy_dandisets(db):
    return {
        'hpf_iri': _seed({'name': 'Hippocampus', 'identifier': f'{OBO}UBERON_0002421'}),
        'hpf_curie': _seed({'name': 'hippocampal formation', 'identifier': 'UBERON:0002421'}),
        'ca1': _seed({'name': 'CA1 field of hippocampus', 'identifier': f'{OBO}UBERON_0003881'}),
        'mba_hpf': _seed({'name': 'Hippocampal formation', 'identifier': f'{MBAO}MBA_1089'}),
        'unidentified': _seed({'name': 'dorsal hippocampus (dHPC)'}),
    }


def _ids(dandisets: dict[str, Dandiset], *keys: str) -> set[str]:
    return {dandisets[key].identifier for key in keys}


@pytest.mark.django_db
@pytest.mark.parametrize(
    'query',
    [
        'anatomy_exact:UBERON:0002421',
        'anatomy_exact:UBERON_0002421',
        'anatomy_exact:http://purl.obolibrary.org/obo/UBERON_0002421',
        'anatomy_exact:"UBERON:0002421"',
    ],
)
def test_anatomy_exact_identifier_matches_every_spelling(api_client, anatomy_dandisets, query):
    # Parts (CA1) and the mouse atlas term are not included.
    assert _search_ids(api_client, query) == _ids(anatomy_dandisets, 'hpf_iri', 'hpf_curie')


@pytest.mark.django_db
def test_anatomy_exact_atlas_identifier(api_client, anatomy_dandisets):
    assert _search_ids(api_client, 'anatomy_exact:MBA:1089') == _ids(anatomy_dandisets, 'mba_hpf')


@pytest.mark.django_db
def test_anatomy_exact_name_matches_the_whole_recorded_name(api_client, anatomy_dandisets):
    assert _search_ids(api_client, 'anatomy_exact:hippocampus') == _ids(
        anatomy_dandisets, 'hpf_iri'
    )
    assert _search_ids(api_client, 'anatomy_exact:"Hippocampal Formation"') == _ids(
        anatomy_dandisets, 'hpf_curie', 'mba_hpf'
    )
    assert _search_ids(api_client, 'anatomy_exact:"dorsal hippocampus (dHPC)"') == _ids(
        anatomy_dandisets, 'unidentified'
    )
    # Regex metacharacters in the value are literal.
    assert _search_ids(api_client, 'anatomy_exact:"dorsal hippocampus .dHPC."') == set()
    assert _search_ids(api_client, 'anatomy_exact:.*') == set()


@pytest.mark.django_db
def test_anatomy_exact_ignores_entries_that_are_not_anatomy(api_client):
    _seed({'name': 'hippocampus', 'identifier': 'UBERON:0002421'}, schema_key='Disorder')
    assert _search_ids(api_client, 'anatomy_exact:hippocampus') == set()
    assert _search_ids(api_client, 'anatomy_exact:UBERON:0002421') == set()


@pytest.mark.django_db
def test_anatomy_exact_repeats_and_combines_on_one_version(api_client, anatomy_dandisets):
    both = _seed(
        {'name': 'CA1', 'identifier': 'UBERON:0003881'},
        {'name': 'cerebral cortex', 'identifier': 'UBERON:0000956'},
    )
    assert _search_ids(
        api_client, 'anatomy_exact:UBERON:0003881 anatomy_exact:"cerebral cortex"'
    ) == {both.identifier}
    assert (
        _search_ids(api_client, 'anatomy_exact:UBERON:0002421 owner:nobody-by-this-name') == set()
    )


@pytest.mark.django_db
def test_bare_lowercase_curie_suggests_anatomy_exact(api_client):
    response = api_client.get('/api/dandisets/', {'search': 'uberon:0002421'})
    assert response.status_code == 400
    assert 'anatomy_exact:UBERON:0002421' in response.json()['search']
