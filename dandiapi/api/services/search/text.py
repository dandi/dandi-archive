"""Free-text search over Version metadata with Postgres full-text search."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.postgres.lookups import Unaccent
from django.db.models import (
    ExpressionWrapper,
    FloatField,
    OuterRef,
    Subquery,
    TextField,
    Value,
)
from django.db.models.expressions import RawSQL
from django.db.models.functions import Cast

from dandiapi.api.models import Version

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from dandiapi.api.models import Dandiset

# Name of the annotation that holds a dandiset's relevance to the free text.
# `DandisetOrderingFilter` orders by it when `ordering=relevance`.
RANK_ANNOTATION = 'search_rank'

_CONFIG = 'english'

# The metadata fields that free text is matched against, grouped by weight
# (A highest). Paths MUST be trusted constants: they're interpolated into the
# SQL. Keys, URLs and schema codes elsewhere in the metadata are deliberately
# left out, so a word like "access" doesn't match every dandiset through
# `dandi:OpenAccess`.
_WEIGHTED_PATHS = {
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
    # `metadata` is left unqualified because Django may alias the Version
    # table in subqueries.
    text = " || ' ' || ".join(f"jsonb_path_query_array(metadata, '{path}')::text" for path in paths)
    return f"setweight(to_tsvector('{_CONFIG}', unaccent({text})), '{weight}')"


SEARCH_VECTOR_SQL = ' || '.join(
    _weighted_vector(weight, paths) for weight, paths in _WEIGHTED_PATHS.items()
)


def _is_identifier_like(term: str) -> bool:
    """Whether `term` should keep substring matching instead of word matching.

    Dandiset identifiers, ORCIDs, DOIs, award numbers and dates all contain
    digits, and the text search parser splits them inconsistently (an ORCID
    inside an orcid.org URL becomes URL parts, while the bare ORCID becomes
    signed integers). Substring matching over the whole metadata finds them
    reliably, and terms with digits rarely match by accident inside other words.
    """
    return any(c.isdigit() for c in term)


def _tsquery_sql(term: str) -> str:
    # A term containing whitespace came from a quoted phrase, so its words
    # must be adjacent.
    fn = 'phraseto_tsquery' if any(c.isspace() for c in term.strip()) else 'plainto_tsquery'
    return f"{fn}('{_CONFIG}', unaccent(%s))"


def apply_free_text(queryset: QuerySet[Dandiset], terms: list[str]) -> QuerySet[Dandiset]:
    """Restrict dandisets to those with a version matching every term, annotated with a rank.

    Words are matched as whole words after stemming ("recordings" matches
    "recording"), within the fields in `_WEIGHTED_PATHS`. A term made only of
    stop words ("the") doesn't constrain the results. Terms that look like
    identifiers keep case-insensitive substring matching over all of the
    metadata, as before. All terms must match the same version. The rank is
    the best `ts_rank` of the word terms among a dandiset's matching versions.
    """
    word_terms = [t for t in terms if not _is_identifier_like(t)]
    versions = Version.objects.alias(_metadata_text=Unaccent(Cast('metadata', TextField())))
    for term in terms:
        if _is_identifier_like(term):
            versions = versions.filter(_metadata_text__icontains=term)
        else:
            tsquery = _tsquery_sql(term)
            versions = versions.extra(  # noqa: S610
                where=[f'(numnode({tsquery}) = 0 OR ({SEARCH_VECTOR_SQL}) @@ {tsquery})'],
                params=[term, term],
            )

    rank = Value(0.0)
    if word_terms:
        combined = ' && '.join(_tsquery_sql(t) for t in word_terms)
        # Normalization 1 divides by 1 + log(document length), so a long
        # description doesn't outrank a title match by repetition alone.
        rank = RawSQL(  # noqa: S611  (trusted constants; user terms are params)
            f'ts_rank(({SEARCH_VECTOR_SQL}), {combined}, 1)', word_terms
        )
    versions = versions.annotate(_rank=ExpressionWrapper(rank, output_field=FloatField()))
    best_rank = versions.filter(dandiset_id=OuterRef('pk')).order_by('-_rank').values('_rank')[:1]
    return queryset.filter(id__in=versions.values_list('dandiset_id', flat=True)).annotate(
        **{RANK_ANNOTATION: Subquery(best_rank, output_field=FloatField())}
    )
