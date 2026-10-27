from __future__ import annotations

from pathlib import Path

import djclick as click

from dandiapi.search.models import OntologyClosure, OntologyTerm
from dandiapi.search.ontology import PACKAGED_ONTOLOGY, ensure_packaged_ontology_loaded


@click.command()
@click.option(
    '--path',
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=PACKAGED_ONTOLOGY,
    show_default=True,
)
@click.option('--force', is_flag=True, help='Reload even if this file is already loaded.')
def load_anatomy_ontology(*, path: Path, force: bool):
    """Load the anatomy ontology tables. `migrate` does this automatically."""
    if ensure_packaged_ontology_loaded(path, force=force):
        click.echo(
            f'Loaded {OntologyTerm.objects.count()} terms and '
            f'{OntologyClosure.objects.count()} closure rows from {path}.'
        )
    else:
        click.echo('The packaged anatomy ontology is already loaded.')
