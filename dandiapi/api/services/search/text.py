"""Free-text search over Version metadata with Postgres full-text search."""

from __future__ import annotations

from functools import reduce
import operator
from typing import TYPE_CHECKING

from django.contrib.postgres.lookups import Unaccent
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import (
    F,
    FloatField,
    Func,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    TextField,
    Value,
)
from django.db.models.functions import Cast

from dandiapi.api.models import Version
from dandiapi.api.services.search.vector import CONFIG

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from dandiapi.api.models import Dandiset

# Name of the annotation that holds a dandiset's relevance to the free text.
# `DandisetOrderingFilter` orders by it when `ordering=relevance`.
RANK_ANNOTATION = 'search_rank'


def _is_identifier_like(term: str) -> bool:
    """Whether `term` should keep substring matching instead of word matching.

    Dandiset identifiers, ORCIDs, DOIs, award numbers and dates all contain
    digits, and the text search parser splits them inconsistently (an ORCID
    inside an orcid.org URL becomes URL parts, while the bare ORCID becomes
    signed integers). Substring matching over the whole metadata finds them
    reliably, and terms with digits rarely match by accident inside other words.
    """
    return any(c.isdigit() for c in term)


def _search_query(term: str) -> SearchQuery:
    # A term containing whitespace came from a quoted phrase, so its words
    # must be adjacent.
    search_type = 'phrase' if any(c.isspace() for c in term.strip()) else 'plain'
    unaccented = Func(Value(term), function='unaccent', output_field=TextField())
    return SearchQuery(unaccented, config=CONFIG, search_type=search_type)


def apply_free_text(queryset: QuerySet[Dandiset], terms: list[str]) -> QuerySet[Dandiset]:
    """Restrict dandisets to those with a version matching every term, annotated with a rank.

    Words are matched as whole words after stemming ("recordings" matches
    "recording") against `Version.search_vector`. A term made only of stop
    words ("the") doesn't constrain the results. Terms that look like
    identifiers keep case-insensitive substring matching over all of the
    metadata. All terms must match the same version. The rank is the best
    `ts_rank` of the word terms among a dandiset's matching versions.
    """
    versions = Version.objects.all()
    if any(_is_identifier_like(term) for term in terms):
        versions = versions.alias(_metadata_text=Unaccent(Cast('metadata', TextField())))
    word_queries = []
    for i, term in enumerate(terms):
        if _is_identifier_like(term):
            versions = versions.filter(_metadata_text__icontains=term)
            continue
        query = _search_query(term)
        word_queries.append(query)
        # `numnode` is 0 for a query made only of stop words.
        lexemes = f'_lexemes_{i}'
        versions = versions.alias(
            **{lexemes: Func(query, function='numnode', output_field=IntegerField())}
        ).filter(Q(search_vector=query) | Q(**{lexemes: 0}))

    if word_queries:
        # Normalization 1 divides by 1 + log(document length), so a long
        # description doesn't outrank a title match by repetition alone.
        rank = SearchRank(
            F('search_vector'), reduce(operator.and_, word_queries), normalization=Value(1)
        )
    else:
        rank = Value(0.0, output_field=FloatField())
    versions = versions.annotate(_rank=rank)
    best_rank = versions.filter(dandiset_id=OuterRef('pk')).order_by('-_rank').values('_rank')[:1]
    return queryset.filter(id__in=versions.values_list('dandiset_id', flat=True)).annotate(
        **{RANK_ANNOTATION: Subquery(best_rank, output_field=FloatField())}
    )
