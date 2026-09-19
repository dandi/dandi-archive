"""Build the anatomy term and closure tables from obographs JSON releases.

The closure is the reachability relation of one directed "contains" graph whose
edges run from a region to the things found inside it:

1. ``is_a`` and ``part_of`` between two anatomy terms. The BICAN atlas
   ontologies assert ``MBA_1089 is_a UBERON_0002421``, so these edges already
   hang each atlas region under its UBERON counterpart.
2. UBERON xrefs to an atlas term, as a fallback for atlas terms whose own
   ontology asserts no UBERON parent.
3. The reverse edge, atlas term to UBERON term, only where the pairing is
   one-to-one within that atlas. A search on ``MBA:1089`` then also finds data
   labeled with the UBERON hippocampal formation. When several atlas terms
   share one UBERON term the reverse edge is left out, because it would let a
   search on a small atlas region climb to a larger UBERON one.

Edges to anything that is not an anatomy term (taxa, cell types) are dropped.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import json
from typing import TYPE_CHECKING, Any
from urllib.request import urlopen

from django.db import transaction

from dandiapi.api.services.search.anatomy import normalize_curie
from dandiapi.search.models import OntologyClosure, OntologyTerm

if TYPE_CHECKING:
    from collections.abc import Iterable

ONTOLOGY_SOURCES: tuple[str, ...] = (
    'http://purl.obolibrary.org/obo/uberon/uberon-base.json',
    'https://raw.githubusercontent.com/brain-bican/mouse_brain_atlas_ontology/main/mbao-base.json',
    'https://raw.githubusercontent.com/brain-bican/human_brain_atlas_ontology/main/hbao-base.json',
    'https://raw.githubusercontent.com/brain-bican/developing_human_brain_atlas_ontology/main/dhbao-base.json',
    'https://raw.githubusercontent.com/brain-bican/developing_mouse_brain_atlas_ontology/main/dmbao-base.json',
)

_PART_OF = 'http://purl.obolibrary.org/obo/BFO_0000050'
_CONTAINMENT_PREDICATES = frozenset({'is_a', _PART_OF})
_REFERENCE_ONTOLOGY = 'UBERON'
_BATCH_SIZE = 10_000


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


def _contains_edges(graph: OntologyGraph) -> dict[str, set[str]]:
    """Return the directed region -> contents adjacency described in the module docstring."""
    known = graph.terms.keys()
    children: dict[str, set[str]] = defaultdict(set)
    # (UBERON term, atlas term) pairs, whichever side asserted them.
    bridges: set[tuple[str, str]] = set()

    for child, parent in graph.containment:
        if child not in known or parent not in known:
            continue
        children[parent].add(child)
        if parent.startswith(f'{_REFERENCE_ONTOLOGY}:') and not child.startswith(
            f'{_REFERENCE_ONTOLOGY}:'
        ):
            bridges.add((parent, child))

    for reference, atlas in graph.xrefs:
        if reference in known and atlas in known:
            children[reference].add(atlas)
            bridges.add((reference, atlas))

    # Reverse edges where the pairing is one-to-one within the atlas.
    atlas_terms_of: dict[tuple[str, str], set[str]] = defaultdict(set)
    reference_terms_of: dict[str, set[str]] = defaultdict(set)
    for reference, atlas in bridges:
        atlas_terms_of[(reference, atlas.split(':', 1)[0])].add(atlas)
        reference_terms_of[atlas].add(reference)
    for reference, atlas in bridges:
        if (
            len(atlas_terms_of[(reference, atlas.split(':', 1)[0])]) == 1
            and len(reference_terms_of[atlas]) == 1
        ):
            children[atlas].add(reference)

    return children


def compute_closure(graph: OntologyGraph) -> Iterable[tuple[str, str]]:
    """Yield every (ancestor, descendant) CURIE pair, including (term, term)."""
    children = _contains_edges(graph)
    for root in graph.terms:
        seen = {root}
        stack = [root]
        while stack:
            for child in children.get(stack.pop(), ()):
                if child not in seen:
                    seen.add(child)
                    stack.append(child)
        for descendant in seen:
            yield root, descendant


def load_graph(sources: Iterable[str]) -> OntologyGraph:
    graph = OntologyGraph()
    for source in sources:
        add_obographs(graph, read_source(source))
    return graph


@transaction.atomic
def replace_ontology_tables(graph: OntologyGraph) -> tuple[int, int]:
    """Replace the term and closure tables with `graph`. Returns (terms, closure rows)."""
    OntologyClosure.objects.all().delete()
    OntologyTerm.objects.all().delete()

    OntologyTerm.objects.bulk_create(
        (
            OntologyTerm(
                curie=term.curie,
                ontology=term.ontology,
                iri=term.iri,
                label=term.label,
                names=sorted({name.lower() for name in (term.label, *term.synonyms)}),
            )
            for term in graph.terms.values()
        ),
        batch_size=_BATCH_SIZE,
    )
    pk_of = dict(OntologyTerm.objects.values_list('curie', 'id'))

    closure_rows = 0
    batch: list[OntologyClosure] = []
    for ancestor, descendant in compute_closure(graph):
        batch.append(OntologyClosure(ancestor_id=pk_of[ancestor], descendant_id=pk_of[descendant]))
        if len(batch) >= _BATCH_SIZE:
            OntologyClosure.objects.bulk_create(batch)
            closure_rows += len(batch)
            batch = []
    OntologyClosure.objects.bulk_create(batch)
    closure_rows += len(batch)

    return len(pk_of), closure_rows
