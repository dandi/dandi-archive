from __future__ import annotations

import json
from typing import TYPE_CHECKING

from django.core.management import call_command
import pytest

from dandiapi.api.services.search.anatomy import normalize_curie
from dandiapi.api.tests.factories import DandisetFactory, DraftVersionFactory
from dandiapi.search.models import OntologyClosure, OntologyRelease, OntologyTerm
from dandiapi.search.ontology import (
    ONTOLOGY_SOURCES,
    UBERON_ROOTS,
    OntologyGraph,
    add_obographs,
    build_package,
    compute_closure,
    ensure_packaged_ontology_loaded,
    read_package,
    write_package,
)

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


# The tests above run with empty ontology tables, where both operators fall
# back to literal identifiers and names. The tests below load a small graph.


@pytest.fixture
def literal_dandisets(db):
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
def test_anatomy_exact_identifier_matches_every_spelling(api_client, literal_dandisets, query):
    # Parts (CA1) and the mouse atlas term are not included.
    assert _search_ids(api_client, query) == _ids(literal_dandisets, 'hpf_iri', 'hpf_curie')


@pytest.mark.django_db
def test_anatomy_exact_atlas_identifier(api_client, literal_dandisets):
    assert _search_ids(api_client, 'anatomy_exact:MBA:1089') == _ids(literal_dandisets, 'mba_hpf')


@pytest.mark.django_db
def test_anatomy_exact_name_matches_the_whole_recorded_name(api_client, literal_dandisets):
    assert _search_ids(api_client, 'anatomy_exact:hippocampus') == _ids(
        literal_dandisets, 'hpf_iri'
    )
    assert _search_ids(api_client, 'anatomy_exact:"Hippocampal Formation"') == _ids(
        literal_dandisets, 'hpf_curie', 'mba_hpf'
    )
    assert _search_ids(api_client, 'anatomy_exact:"dorsal hippocampus (dHPC)"') == _ids(
        literal_dandisets, 'unidentified'
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
def test_anatomy_exact_repeats_and_combines_on_one_version(api_client, literal_dandisets):
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
def test_bare_lowercase_curie_suggests_the_anatomy_operator(api_client):
    response = api_client.get('/api/dandisets/', {'search': 'uberon:0002421'})
    assert response.status_code == 400
    assert 'anatomy:UBERON:0002421' in response.json()['search']


@pytest.mark.django_db
def test_anatomy_without_ontology_tables_matches_literally(api_client):
    hpf = _seed({'name': 'Hippocampus', 'identifier': f'{OBO}UBERON_0002421'})
    _seed({'name': 'CA1 field', 'identifier': f'{OBO}UBERON_0003881'})
    assert _search_ids(api_client, 'anatomy:UBERON:0002421') == {hpf.identifier}
    assert _search_ids(api_client, 'anatomy:hippocampus') == {hpf.identifier}


PART_OF = f'{OBO}BFO_0000050'

NERVOUS_SYSTEM = 'UBERON:0001016'
BRAIN = 'UBERON:0000955'
HIPPOCAMPAL_FORMATION = 'UBERON:0002421'
AMMONS_HORN = 'UBERON:0001954'
CA1 = 'UBERON:0003881'
CORTEX = 'UBERON:0000956'
HEART = 'UBERON:0000948'
MBA_HPF = 'MBA:1089'
MBA_CA1 = 'MBA:382'
MBA_CORTEX_A = 'MBA:688'
MBA_CORTEX_B = 'MBA:695'


def _node(iri: str, label: str, *, synonyms: tuple[str, ...] = (), xrefs: tuple[str, ...] = ()):
    return {
        'id': iri,
        'lbl': label,
        'type': 'CLASS',
        'meta': {
            'synonyms': [{'pred': 'hasRelatedSynonym', 'val': s} for s in synonyms],
            'xrefs': [{'val': x} for x in xrefs],
        },
    }


def _edge(sub: str, pred: str, obj: str):
    return {'sub': sub, 'pred': pred, 'obj': obj}


# A cut-down UBERON: nervous system > brain > hippocampal formation > Ammon's
# horn > CA1, all by part_of, plus cerebral cortex, and a heart outside the
# nervous system. The hippocampal formation is reached from the mouse atlas
# only through a UBERON xref; CA1 only through an atlas is_a edge.
UBERON_DOCUMENT = {
    'graphs': [
        {
            'nodes': [
                _node(f'{OBO}UBERON_0001016', 'nervous system'),
                _node(f'{OBO}UBERON_0000955', 'brain'),
                _node(
                    f'{OBO}UBERON_0002421',
                    'hippocampal formation',
                    synonyms=('hippocampus',),
                    xrefs=('MBA:1089', 'FMA:74038'),
                ),
                _node(f'{OBO}UBERON_0001954', "Ammon's horn"),
                _node(f'{OBO}UBERON_0003881', 'CA1 field of hippocampus'),
                _node(f'{OBO}UBERON_0000956', 'cerebral cortex'),
                _node(f'{OBO}UBERON_0000948', 'heart'),
                _node(f'{OBO}UBERON_9999999', 'obsolete thing') | {'meta': {'deprecated': True}},
                _node(f'{OBO}NCBITaxon_10090', 'Mus musculus'),
            ],
            'edges': [
                _edge(f'{OBO}UBERON_0000955', PART_OF, f'{OBO}UBERON_0001016'),
                _edge(f'{OBO}UBERON_0002421', PART_OF, f'{OBO}UBERON_0000955'),
                _edge(f'{OBO}UBERON_0001954', PART_OF, f'{OBO}UBERON_0002421'),
                _edge(f'{OBO}UBERON_0003881', PART_OF, f'{OBO}UBERON_0001954'),
                _edge(f'{OBO}UBERON_0000956', PART_OF, f'{OBO}UBERON_0000955'),
                _edge(f'{OBO}UBERON_0000955', f'{OBO}RO_0002202', f'{OBO}UBERON_0000956'),
            ],
        }
    ]
}

# A cut-down mouse atlas.
MBA_DOCUMENT = {
    'graphs': [
        {
            'nodes': [
                _node(f'{MBAO}MBA_997', 'root'),
                _node(f'{MBAO}MBA_1089', 'Hippocampal formation', synonyms=('HPF',)),
                _node(f'{MBAO}MBA_382', 'Field CA1', synonyms=('CA1',)),
                _node(f'{MBAO}MBA_688', 'Cerebral cortex'),
                _node(f'{MBAO}MBA_695', 'Cortical plate'),
            ],
            'edges': [
                _edge(f'{MBAO}MBA_1089', PART_OF, f'{MBAO}MBA_997'),
                _edge(f'{MBAO}MBA_382', PART_OF, f'{MBAO}MBA_1089'),
                _edge(f'{MBAO}MBA_382', 'is_a', f'{OBO}UBERON_0003881'),
                _edge(f'{MBAO}MBA_688', PART_OF, f'{MBAO}MBA_997'),
                _edge(f'{MBAO}MBA_695', PART_OF, f'{MBAO}MBA_688'),
                _edge(f'{MBAO}MBA_688', 'is_a', f'{OBO}UBERON_0000956'),
                _edge(f'{MBAO}MBA_695', 'is_a', f'{OBO}UBERON_0000956'),
                _edge(f'{MBAO}MBA_1089', PART_OF, f'{OBO}NCBITaxon_10090'),
            ],
        }
    ]
}

FIXTURE_SOURCES = ('uberon.json', 'mba.json')


def _fixture_graph() -> OntologyGraph:
    graph = OntologyGraph()
    add_obographs(graph, UBERON_DOCUMENT)
    add_obographs(graph, MBA_DOCUMENT)
    return graph


def _fixture_package() -> dict:
    return build_package(_fixture_graph(), FIXTURE_SOURCES)


def _descendants(package: dict) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for ancestor, descendant in compute_closure(package):
        result.setdefault(ancestor, set()).add(descendant)
    return result


def test_add_obographs_keeps_only_live_anatomy_terms():
    graph = _fixture_graph()
    assert 'UBERON:9999999' not in graph.terms
    assert not any(curie.startswith('NCBITAXON') for curie in graph.terms)
    assert graph.terms[HIPPOCAMPAL_FORMATION].synonyms == ['hippocampus']
    # Only xrefs to a known atlas are kept.
    assert graph.xrefs == {(HIPPOCAMPAL_FORMATION, MBA_HPF)}


def test_package_keeps_the_nervous_system_and_every_atlas_term():
    curies = {curie for curie, *_ in _fixture_package()['terms']}
    assert HEART not in curies
    assert {NERVOUS_SYSTEM, BRAIN, CA1, CORTEX} <= curies
    assert {'MBA:997', MBA_HPF, MBA_CA1} <= curies


def test_closure_follows_part_of_downward_only():
    descendants = _descendants(_fixture_package())
    assert {HIPPOCAMPAL_FORMATION, AMMONS_HORN, CA1} <= descendants[HIPPOCAMPAL_FORMATION]
    assert BRAIN not in descendants[HIPPOCAMPAL_FORMATION]
    assert HIPPOCAMPAL_FORMATION not in descendants[CA1]
    # Predicates other than is_a / part_of are not containment.
    assert BRAIN not in descendants[CORTEX]


def test_closure_reaches_atlases_from_uberon_but_not_the_reverse():
    descendants = _descendants(_fixture_package())
    # UBERON -> atlas, via the UBERON xref and via the atlas is_a edge.
    assert {MBA_HPF, MBA_CA1} <= descendants[HIPPOCAMPAL_FORMATION]
    assert MBA_CA1 in descendants[CA1]
    assert {MBA_CORTEX_A, MBA_CORTEX_B} <= descendants[CORTEX]
    # An atlas term is specific to one species, so it never reaches UBERON.
    assert descendants[MBA_HPF] == {MBA_HPF, MBA_CA1}
    assert descendants[MBA_CA1] == {MBA_CA1}
    assert descendants[MBA_CORTEX_A] == {MBA_CORTEX_A, MBA_CORTEX_B}


def test_package_file_round_trips_reproducibly(tmp_path):
    package = _fixture_package()
    first, second = tmp_path / 'a.json.gz', tmp_path / 'b.json.gz'
    write_package(package, first)
    write_package(package, second)
    assert first.read_bytes() == second.read_bytes()
    loaded, checksum = read_package(first)
    assert loaded == package
    assert len(checksum) == 64


def test_pinned_sources_are_pinned():
    for source in ONTOLOGY_SOURCES:
        assert '/main/' not in source
        assert '/latest/' not in source


def test_packaged_ontology_was_built_from_the_pinned_sources():
    package, _ = read_package()
    assert package['sources'] == list(ONTOLOGY_SOURCES)
    assert package['uberon_roots'] == list(UBERON_ROOTS)
    assert any(curie == HIPPOCAMPAL_FORMATION for curie, *_ in package['terms'])


@pytest.fixture
def package_file(tmp_path):
    path = tmp_path / 'anatomy_ontology.json.gz'
    write_package(_fixture_package(), path)
    return path


@pytest.fixture
def ontology_tables(db, package_file):
    assert ensure_packaged_ontology_loaded(package_file)


@pytest.mark.django_db
def test_load_records_the_release_and_skips_an_unchanged_file(package_file):
    assert ensure_packaged_ontology_loaded(package_file)
    _, checksum = read_package(package_file)
    release = OntologyRelease.objects.get()
    assert release.checksum == checksum
    assert release.sources == list(FIXTURE_SOURCES)
    term = OntologyTerm.objects.get(curie=HIPPOCAMPAL_FORMATION)
    assert term.names == ['hippocampal formation', 'hippocampus']
    assert term.ontology == 'UBERON'
    counts = (OntologyTerm.objects.count(), OntologyClosure.objects.count())

    assert not ensure_packaged_ontology_loaded(package_file)
    assert OntologyRelease.objects.count() == 1

    assert ensure_packaged_ontology_loaded(package_file, force=True)
    assert OntologyRelease.objects.count() == 2
    assert (OntologyTerm.objects.count(), OntologyClosure.objects.count()) == counts


@pytest.mark.django_db
def test_a_changed_package_replaces_the_tables(tmp_path, package_file):
    ensure_packaged_ontology_loaded(package_file)
    smaller = _fixture_package()
    smaller['terms'] = [t for t in smaller['terms'] if t[0] != CORTEX]
    smaller['contains'] = [e for e in smaller['contains'] if CORTEX not in e]
    path = tmp_path / 'smaller.json.gz'
    write_package(smaller, path)

    assert ensure_packaged_ontology_loaded(path)
    assert not OntologyTerm.objects.filter(curie=CORTEX).exists()
    assert OntologyRelease.objects.count() == 2


@pytest.mark.django_db
def test_build_and_load_commands(tmp_path):
    uberon = tmp_path / 'uberon.json'
    uberon.write_text(json.dumps(UBERON_DOCUMENT))
    mba = tmp_path / 'mba.json'
    mba.write_text(json.dumps(MBA_DOCUMENT))
    output = tmp_path / 'out.json.gz'

    call_command(
        'build_anatomy_ontology',
        '--source',
        str(uberon),
        '--source',
        str(mba),
        '--output',
        str(output),
    )
    call_command('load_anatomy_ontology', '--path', str(output))

    assert OntologyTerm.objects.count() == len(read_package(output)[0]['terms'])
    assert OntologyClosure.objects.filter(
        ancestor__curie=HIPPOCAMPAL_FORMATION, descendant__curie=MBA_CA1
    ).exists()


@pytest.mark.django_db
def test_migrate_loads_the_packaged_ontology_only_when_enabled(settings, monkeypatch, package_file):
    monkeypatch.setattr('dandiapi.search.ontology.PACKAGED_ONTOLOGY', package_file)
    monkeypatch.setattr(ensure_packaged_ontology_loaded, '__defaults__', (package_file,))

    call_command('migrate', verbosity=0)
    assert not OntologyRelease.objects.exists()

    settings.DANDI_ANATOMY_ONTOLOGY_AUTOLOAD = True
    call_command('migrate', verbosity=0)
    assert OntologyRelease.objects.count() == 1
    call_command('migrate', verbosity=0)
    assert OntologyRelease.objects.count() == 1


@pytest.fixture
def anatomy_dandisets(ontology_tables):
    return {
        'brain': _seed({'name': 'brain', 'identifier': f'{OBO}UBERON_0000955'}),
        'hpf': _seed({'name': 'Hippocampus', 'identifier': 'UBERON:0002421'}),
        'ca1': _seed({'name': 'CA1 field of hippocampus', 'identifier': f'{OBO}UBERON_0003881'}),
        'mba_ca1': _seed({'name': 'Field CA1', 'identifier': f'{MBAO}MBA_382'}),
        'cortex': _seed({'name': 'cerebral cortex', 'identifier': f'{OBO}UBERON_0000956'}),
        'unidentified': _seed({'name': 'dorsal hippocampus (dHPC)'}),
        'cell_type': _seed({'name': 'pyramidal neuron', 'identifier': f'{OBO}CL_0000598'}),
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    'query',
    [
        'anatomy:UBERON:0002421',
        'anatomy:uberon:0002421',
        'anatomy:UBERON_0002421',
        'anatomy:http://purl.obolibrary.org/obo/UBERON_0002421',
    ],
)
def test_anatomy_identifier_expands_to_parts_and_other_atlases(
    api_client, anatomy_dandisets, query
):
    assert _search_ids(api_client, query) == _ids(anatomy_dandisets, 'hpf', 'ca1', 'mba_ca1')


@pytest.mark.django_db
@pytest.mark.parametrize(
    'query',
    ['anatomy:MBA:1089', 'anatomy:https://purl.brain-bican.org/ontology/mbao/MBA_1089'],
)
def test_anatomy_atlas_identifier_stays_inside_its_atlas(api_client, anatomy_dandisets, query):
    # MBA regions describe the mouse brain, so UBERON-labeled data is not returned.
    assert _search_ids(api_client, query) == _ids(anatomy_dandisets, 'mba_ca1')


@pytest.mark.django_db
def test_anatomy_label_search_also_matches_recorded_names(api_client, anatomy_dandisets):
    # "hippocampus" is a synonym of the hippocampal formation, and a whole word
    # in the name of the entry that has no identifier.
    assert _search_ids(api_client, 'anatomy:hippocampus') == _ids(
        anatomy_dandisets, 'hpf', 'ca1', 'mba_ca1', 'unidentified'
    )
    assert _search_ids(api_client, 'anatomy:"cerebral cortex"') == _ids(anatomy_dandisets, 'cortex')


@pytest.mark.django_db
def test_anatomy_label_falls_back_to_substring_of_term_labels(api_client, anatomy_dandisets):
    # No term is named exactly "ammon", but one label contains it.
    assert _search_ids(api_client, 'anatomy:ammon') == _ids(anatomy_dandisets, 'ca1', 'mba_ca1')


@pytest.mark.django_db
def test_anatomy_exact_does_not_expand(api_client, anatomy_dandisets):
    assert _search_ids(api_client, 'anatomy_exact:UBERON:0002421') == _ids(anatomy_dandisets, 'hpf')
    # By name, the term is resolved through its synonym and the recorded name
    # has to match in full, so "CA1 field of hippocampus" stays out.
    assert _search_ids(api_client, 'anatomy_exact:hippocampus') == _ids(anatomy_dandisets, 'hpf')
    assert _search_ids(api_client, 'anatomy_exact:"dorsal hippocampus (dHPC)"') == _ids(
        anatomy_dandisets, 'unidentified'
    )


@pytest.mark.django_db
def test_anatomy_search_on_a_small_region_does_not_return_larger_ones(
    api_client, anatomy_dandisets
):
    assert _search_ids(api_client, 'anatomy:MBA:382') == _ids(anatomy_dandisets, 'mba_ca1')
    assert _search_ids(api_client, 'anatomy:UBERON:0003881') == _ids(
        anatomy_dandisets, 'ca1', 'mba_ca1'
    )
    assert _search_ids(api_client, 'anatomy:UBERON:0000955') == _ids(
        anatomy_dandisets, 'brain', 'hpf', 'ca1', 'mba_ca1', 'cortex'
    )


@pytest.mark.django_db
def test_anatomy_outside_the_packaged_graph_still_matches_literally(api_client, ontology_tables):
    heart = _seed({'name': 'heart', 'identifier': f'{OBO}UBERON_0000948'})
    assert _search_ids(api_client, 'anatomy:UBERON:0000948') == {heart.identifier}
    assert _search_ids(api_client, 'anatomy:heart') == {heart.identifier}


@pytest.mark.django_db
def test_anatomy_combines_with_other_operators_and_repeats(api_client, anatomy_dandisets):
    both = _seed(
        {'name': 'CA1', 'identifier': 'UBERON:0003881'},
        {'name': 'cerebral cortex', 'identifier': 'UBERON:0000956'},
    )
    assert _search_ids(api_client, 'anatomy:hippocampus anatomy:"cerebral cortex"') == {
        both.identifier
    }
    assert _search_ids(api_client, 'anatomy:hippocampus owner:nobody-by-this-name') == set()


@pytest.mark.django_db
def test_anatomy_name_matching_is_by_whole_word_on_anatomy_entries_only(
    api_client, ontology_tables
):
    _seed({'name': 'hippocampus sclerosis'}, schema_key='Disorder')
    thalamus = _seed({'name': 'Thalamus (TH)'})
    _seed({'name': 'hypothalamus'})
    assert _search_ids(api_client, 'anatomy:hippocampus') == set()
    # Names match on whole words, so "hypothalamus" is not a hit for "thalamus".
    assert _search_ids(api_client, 'anatomy:thalamus') == {thalamus.identifier}
    assert _search_ids(api_client, 'anatomy:%') == set()
    assert _search_ids(api_client, 'anatomy:thal_mus') == set()


@pytest.mark.django_db
def test_anatomy_entry_with_a_known_identifier_is_not_matched_by_name(api_client, ontology_tables):
    # The label mentions the cortex, but the identifier says CA1.
    _seed({'name': 'CA1, below the cerebral cortex', 'identifier': 'UBERON:0003881'})
    assert _search_ids(api_client, 'anatomy:"cerebral cortex"') == set()
