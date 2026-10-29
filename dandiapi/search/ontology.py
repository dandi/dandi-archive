"""Build the packaged anatomy ontology and answer containment queries from it.

A term's descendants are what it reaches in one directed "contains" graph whose
edges run from a region to the things found inside it:

1. ``is_a`` and ``part_of`` between two anatomy terms. The BICAN atlas
   ontologies assert ``MBA_1089 is_a UBERON_0002421``, so these edges already
   hang each atlas region under its UBERON counterpart.
2. UBERON xrefs to an atlas term, as a fallback for atlas terms whose own
   ontology asserts no UBERON parent.

There is no edge from an atlas term to a UBERON term. UBERON is cross-species,
so a UBERON search reaches every atlas, but an atlas term is specific to one
species and a search on ``MBA:1089`` stays inside the mouse atlas.

Edges to anything that is not an anatomy term (taxa, cell types) are dropped.

``manage.py build_anatomy_ontology`` downloads the releases pinned in
:data:`ONTOLOGY_SOURCES`, keeps the nervous system, the sense organs, and the
atlas terms, and writes the terms and edges to :data:`PACKAGED_ONTOLOGY`,
which is committed. Updating the ontologies is a pull request that changes the
pins and that file.

Nothing about the ontology is stored in the database. Each process reads the
packaged file once, on its first anatomy search, into an
:class:`AnatomyOntology`, which resolves names and expands a term to everything
it contains. The search then matches the resulting CURIEs against the
Dandiset metadata.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from functools import cache
import gzip
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.request import urlopen

from django.conf import settings

from dandiapi.api.services.search.anatomy import normalize_curie

if TYPE_CHECKING:
    from collections.abc import Iterable

# Pinned releases. UBERON by release tag, the BICAN atlases by commit.
ONTOLOGY_SOURCES: tuple[str, ...] = (
    'https://github.com/obophenotype/uberon/releases/download/v2026-10-01/uberon-base.json',
    (
        'https://raw.githubusercontent.com/brain-bican/mouse_brain_atlas_ontology/'
        '96ec7312da94b10d047ba84bc89cf3c2729f1811/mbao-base.json'
    ),
    (
        'https://raw.githubusercontent.com/brain-bican/human_brain_atlas_ontology/'
        '3ff272135c917b0437edc4cab7d23bd25f05244b/hbao-base.json'
    ),
    (
        'https://raw.githubusercontent.com/brain-bican/developing_human_brain_atlas_ontology/'
        '5039f6900b4ca96bc20824769cb717ec3e3b1a9c/dhbao-base.json'
    ),
    (
        'https://raw.githubusercontent.com/brain-bican/developing_mouse_brain_atlas_ontology/'
        '8a5c7344baddb123f31c43989ce57b011800ff90/dmbao-base.json'
    ),
)

# UBERON terms are kept only if they are inside one of these. Atlas terms are
# all kept. Identifiers outside this set still match literally and by name.
UBERON_ROOTS: tuple[str, ...] = (
    'UBERON:0001016',  # nervous system
    'UBERON:0000020',  # sense organ
)

PACKAGED_ONTOLOGY = Path(__file__).parent / 'data' / 'anatomy_ontology.json.gz'

_PART_OF = 'http://purl.obolibrary.org/obo/BFO_0000050'
_CONTAINMENT_PREDICATES = frozenset({'is_a', _PART_OF})
_REFERENCE_ONTOLOGY = 'UBERON'


@dataclass
class Term:
    curie: str
    iri: str
    label: str
    synonyms: list[str] = field(default_factory=list)

    @property
    def ontology(self) -> str:
        return self.curie.split(':', 1)[0]


@dataclass
class OntologyGraph:
    terms: dict[str, Term] = field(default_factory=dict)
    # (child, parent) pairs from is_a / part_of.
    containment: set[tuple[str, str]] = field(default_factory=set)
    # (UBERON term, atlas term) pairs from UBERON xrefs.
    xrefs: set[tuple[str, str]] = field(default_factory=set)


def read_source(source: str) -> dict[str, Any]:
    """Load one obographs JSON document from a URL or a local path."""
    if source.startswith(('http://', 'https://')):
        with urlopen(source) as response:  # noqa: S310 - scheme checked above
            return json.load(response)
    with open(source) as stream:  # noqa: PTH123
        return json.load(stream)


def _add_node(graph: OntologyGraph, node: dict[str, Any]) -> None:
    curie = normalize_curie(node.get('id'))
    meta = node.get('meta') or {}
    # A node with no label is a bare reference to a term that another source defines.
    if (
        curie is None
        or node.get('type') != 'CLASS'
        or meta.get('deprecated')
        or not node.get('lbl')
    ):
        return
    graph.terms[curie] = Term(
        curie=curie,
        iri=node['id'],
        label=node['lbl'],
        synonyms=[s['val'] for s in meta.get('synonyms', []) if s.get('val')],
    )
    if not curie.startswith(f'{_REFERENCE_ONTOLOGY}:'):
        return
    for xref in meta.get('xrefs', []):
        target = normalize_curie(xref.get('val'))
        if target and not target.startswith(f'{_REFERENCE_ONTOLOGY}:'):
            graph.xrefs.add((curie, target))


def _add_edge(graph: OntologyGraph, edge: dict[str, Any]) -> None:
    if edge.get('pred') not in _CONTAINMENT_PREDICATES:
        return
    child = normalize_curie(edge.get('sub'))
    parent = normalize_curie(edge.get('obj'))
    if child and parent and child != parent:
        graph.containment.add((child, parent))


def add_obographs(graph: OntologyGraph, document: dict[str, Any]) -> None:
    """Merge the anatomy terms and edges of an obographs document into `graph`."""
    for obograph in document.get('graphs', []):
        for node in obograph.get('nodes', []):
            _add_node(graph, node)
        for edge in obograph.get('edges', []):
            _add_edge(graph, edge)


def load_graph(sources: Iterable[str]) -> OntologyGraph:
    graph = OntologyGraph()
    for source in sources:
        add_obographs(graph, read_source(source))
    return graph


def _contains_edges(graph: OntologyGraph) -> dict[str, set[str]]:
    """Return the directed region -> contents adjacency described in the module docstring."""
    known = graph.terms.keys()
    children: dict[str, set[str]] = defaultdict(set)
    for child, parent in (*graph.containment, *((atlas, ref) for ref, atlas in graph.xrefs)):
        if child not in known or parent not in known:
            continue
        # Nothing species-specific may contain a cross-species UBERON term.
        if child.startswith(f'{_REFERENCE_ONTOLOGY}:') and not parent.startswith(
            f'{_REFERENCE_ONTOLOGY}:'
        ):
            continue
        children[parent].add(child)
    return children


def _reachable(children: dict[str, set[str]], root: str) -> set[str]:
    seen = {root}
    stack = [root]
    while stack:
        for child in children.get(stack.pop(), ()):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return seen


def build_package(
    graph: OntologyGraph,
    sources: Iterable[str],
    uberon_roots: Iterable[str] = UBERON_ROOTS,
) -> dict[str, Any]:
    """Reduce `graph` to the packaged form: kept terms and the contains edges between them."""
    children = _contains_edges(graph)
    kept: set[str] = {
        curie for curie in graph.terms if not curie.startswith(f'{_REFERENCE_ONTOLOGY}:')
    }
    for root in uberon_roots:
        if root in graph.terms:
            kept |= _reachable(children, root)
    return {
        'sources': list(sources),
        'uberon_roots': list(uberon_roots),
        'terms': [
            [term.curie, term.iri, term.label, sorted(set(term.synonyms))]
            for term in sorted(graph.terms.values(), key=lambda t: t.curie)
            if term.curie in kept
        ],
        'contains': sorted(
            [parent, child]
            for parent, contents in children.items()
            if parent in kept
            for child in contents
            if child in kept
        ),
    }


def write_package(package: dict[str, Any], path: Path) -> None:
    """Write `package` as gzipped JSON, byte-for-byte reproducible."""
    data = json.dumps(package, sort_keys=True, separators=(',', ':')).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with (
        path.open('wb') as raw,
        gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as stream,
    ):
        stream.write(data)


def read_package(path: Path = PACKAGED_ONTOLOGY) -> dict[str, Any]:
    """Return the packaged ontology."""
    return json.loads(gzip.decompress(path.read_bytes()))


class AnatomyOntology:
    """The packaged ontology held in memory: term names and the contains graph."""

    def __init__(self, package: dict[str, Any] | None = None) -> None:
        package = package or {'terms': [], 'contains': []}
        self.labels: dict[str, str] = {}
        # Lowercased label or synonym -> the CURIEs that carry it.
        self._by_name: dict[str, set[str]] = defaultdict(set)
        self._children: dict[str, set[str]] = defaultdict(set)
        for curie, _iri, label, synonyms in package['terms']:
            self.labels[curie] = label
            for name in (label, *synonyms):
                self._by_name[name.lower()].add(curie)
        for parent, child in package['contains']:
            self._children[parent].add(child)

    def __contains__(self, curie: object) -> bool:
        return curie in self.labels

    def find(self, name: str) -> set[str]:
        """Return the terms with `name` as label or synonym, else those whose label contains it."""
        exact = self._by_name.get(name.lower())
        if exact:
            return set(exact)
        needle = name.lower()
        return {curie for curie, label in self.labels.items() if needle in label.lower()}

    def descendants(self, curie: str) -> set[str]:
        """Return `curie` and every term it contains, directly or not."""
        return _reachable(self._children, curie)


@cache
def _load(path: str) -> AnatomyOntology:
    return AnatomyOntology(read_package(Path(path)))


def anatomy_ontology() -> AnatomyOntology:
    """Return the ontology named by `DANDI_ANATOMY_ONTOLOGY_PATH`, or an empty one if unset."""
    path = settings.DANDI_ANATOMY_ONTOLOGY_PATH
    if not path:
        return AnatomyOntology()
    return _load(str(path))
