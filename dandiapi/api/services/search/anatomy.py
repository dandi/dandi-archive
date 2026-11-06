"""Identifier handling for the ``anatomy:`` search operators.

Anatomy identifiers reach the archive in several spellings: OBO PURLs
(``http://purl.obolibrary.org/obo/UBERON_0002421``), BICAN PURLs
(``https://purl.brain-bican.org/ontology/mbao/MBA_1089``), CURIEs
(``UBERON:0002421``) and the underscore form (``UBERON_0002421``). Everything
here reduces them to one canonical CURIE, ``PREFIX:digits`` with an uppercase
prefix.

This module is pure Python so that the parser can import it without pulling
in any models.
"""

from __future__ import annotations

import re
from urllib.parse import unquote

# Ontologies whose terms the anatomy operators understand. UBERON is the
# cross-species reference; the rest are the Allen atlases published by BICAN.
ANATOMY_ONTOLOGIES: tuple[str, ...] = ('UBERON', 'MBA', 'HBA', 'DHBA', 'DMBA')

_PREFIX_ALTERNATION = '|'.join(ANATOMY_ONTOLOGIES)
_CURIE_RE = re.compile(rf'(?:^|[^A-Za-z])({_PREFIX_ALTERNATION})[_:](\d+)$', re.IGNORECASE)


def normalize_curie(identifier: str | None) -> str | None:
    """Return the canonical CURIE for an anatomy identifier, or None if it isn't one."""
    if not identifier:
        return None
    match = _CURIE_RE.search(unquote(identifier.strip()))
    if match is None:
        return None
    return f'{match.group(1).upper()}:{match.group(2)}'
