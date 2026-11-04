"""The full-text search vector stored on each Version.

`Version.search_vector` is a stored generated column computed by Postgres from
`metadata`, so it stays current however the metadata is written, including
queryset `.update()` calls. This module has no model imports so that the model
can import it.
"""

from __future__ import annotations

CONFIG = 'english'

# A generated column's expression must be immutable, and `unaccent` is only
# stable (its dictionary could change), so it's wrapped in a function declared
# immutable. Created by migration 0034_version_search_vector.
IMMUTABLE_UNACCENT = 'dandi_immutable_unaccent'

# The metadata fields that free text is matched against, grouped by weight
# (A highest). Keys, URLs and schema codes elsewhere in the metadata are
# deliberately left out, so a word like "access" doesn't match every dandiset
# through `dandi:OpenAccess`. Changing these needs a migration that alters the
# generated column.
WEIGHTED_PATHS = {
    'A': ['$.name', '$.identifier'],
    'B': [
        '$.keywords[*]',
        '$.about[*].name',
        '$.assetsSummary.species[*].name',
        '$.assetsSummary.approach[*].name',
        '$.assetsSummary.measurementTechnique[*].name',
        '$.assetsSummary.dataStandard[*].name',
        '$.assetsSummary.variableMeasured[*]',
    ],
    'C': ['$.description'],
    'D': [
        '$.contributor[*].name',
        '$.contributor[*].identifier',
        '$.contributor[*].awardNumber',
        '$.contributor[*].affiliation[*].name',
    ],
}


def _weighted_vector(weight: str, paths: list[str]) -> str:
    # `jsonb_path_query_array(...)::text` renders the matched values as a JSON
    # array; the text search parser drops the brackets, quotes and commas.
    text = " || ' ' || ".join(f"jsonb_path_query_array(metadata, '{path}')::text" for path in paths)
    return f"setweight(to_tsvector('{CONFIG}', {IMMUTABLE_UNACCENT}({text})), '{weight}')"


SEARCH_VECTOR_SQL = ' || '.join(
    _weighted_vector(weight, paths) for weight, paths in WEIGHTED_PATHS.items()
)
