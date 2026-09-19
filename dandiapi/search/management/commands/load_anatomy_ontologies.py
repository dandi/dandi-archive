from __future__ import annotations

import djclick as click

from dandiapi.search.ontology import ONTOLOGY_SOURCES, load_graph, replace_ontology_tables


@click.command()
@click.option(
    '--source',
    'sources',
    multiple=True,
    help='URL or path of an obographs JSON file. Repeatable. Defaults to UBERON and the '
    'BICAN Allen atlas ontologies.',
)
def load_anatomy_ontologies(*, sources: tuple[str, ...]):
    """Rebuild the ontology tables behind the anatomy search operators."""
    graph = load_graph(sources or ONTOLOGY_SOURCES)
    terms, closure_rows = replace_ontology_tables(graph)
    click.echo(f'Loaded {terms} terms and {closure_rows} closure rows.')
