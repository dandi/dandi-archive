from __future__ import annotations

from pathlib import Path

import djclick as click

from dandiapi.search.ontology import (
    ONTOLOGY_SOURCES,
    PACKAGED_ONTOLOGY,
    build_package,
    load_graph,
    write_package,
)


@click.command()
@click.option(
    '--source',
    'sources',
    multiple=True,
    help='URL or path of an obographs JSON file. Repeatable. Defaults to the pinned releases.',
)
@click.option(
    '--output',
    type=click.Path(dir_okay=False, path_type=Path),
    default=PACKAGED_ONTOLOGY,
    show_default=True,
)
def build_anatomy_ontology(*, sources: tuple[str, ...], output: Path):
    """Rebuild the packaged anatomy ontology from obographs releases.

    Run this after changing the pinned sources, then commit the output file.
    """
    sources = sources or ONTOLOGY_SOURCES
    package = build_package(load_graph(sources), sources)
    write_package(package, output)
    click.echo(
        f'Wrote {len(package["terms"])} terms and {len(package["contains"])} edges to {output}.'
    )
