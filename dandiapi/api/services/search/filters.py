"""Compile a parsed search query into a Postgres filter on the Dandiset queryset.

``build_search_filter`` parses the query with
:func:`~dandiapi.api.services.search.parser.parse_search` and turns every term
into one SQL predicate:

- free text (``word`` / ``"phrase"``): case-insensitive, accent-insensitive
  substring match on the text of a version's metadata
- ``species:`` / ``approach:`` / ``technique:`` / ``standard:`` /
  ``variable:``: a ``jsonb_path_exists`` regex match on the version's
  ``assetsSummary``
- ``created_*`` / ``modified_*`` / ``published_*``: a comparison on the
  dandiset's creation time or on its latest (published) version
- ``anatomy_exact:``: an Anatomy entry in the version's ``about`` with the
  given identifier (in any spelling) or exactly the given name
- ``owner:``: membership in the set of dandisets owned by matching users

Version-level predicates (free text, summary and anatomy operators) are AND'd and must
all hold on a single Version row; that row's dandiset is then AND'd with the
dandiset-level predicates. The result is one ``Q`` the view applies with
``queryset.filter``.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.contrib.postgres.lookups import Unaccent
from django.db.models import BooleanField, F, Func, OuterRef, Q, Subquery, TextField, Value
from django.db.models.expressions import RawSQL
from django.db.models.functions import Cast, Concat
from django.db.models.lookups import GreaterThanOrEqual, IContains, LessThan

from dandiapi.api.models import Version
from dandiapi.api.models.dandiset import DandisetUserObjectPermission
from dandiapi.api.services.search.anatomy import CURIE_SQL_TEMPLATE, normalize_curie
from dandiapi.api.services.search.parser import parse_date, parse_search

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from dandiapi.api.models import Dandiset

_LATEST_VERSION_MODIFIED = Subquery(
    Version.objects.filter(dandiset=OuterRef('pk')).order_by('-created').values('modified')[:1]
)
_LATEST_PUBLISHED_CREATED = Subquery(
    Version.objects.filter(dandiset=OuterRef('pk'))
    .exclude(version='draft')
    .order_by('-created')
    .values('created')[:1]
)


# Maps each operator to a Postgres jsonpath into the version-level
# `assetsSummary` aggregation. `variableMeasured` holds bare strings rather
# than objects with a `name`, so its path selects the elements themselves.
_SUMMARY_PATH_OPS = {
    'species': '$.assetsSummary.species[*].name',
    'approach': '$.assetsSummary.approach[*].name',
    'technique': '$.assetsSummary.measurementTechnique[*].name',
    'standard': '$.assetsSummary.dataStandard[*].name',
    'variable': '$.assetsSummary.variableMeasured[*]',
}


class _JsonbPathExists(Func):
    """``jsonb_path_exists(<expression>, <path>::jsonpath)``, usable as a filter."""

    template = '%(function)s(%(expressions)s::jsonpath)'
    function = 'jsonb_path_exists'
    output_field = BooleanField()


def _summary_predicate(operator: str, value: str) -> _JsonbPathExists:
    """Match ``value`` case-insensitively against the operator's summary entries.

    The whole jsonpath is sent as a bound parameter, so nothing user-supplied
    is interpolated into the SQL. Inside the jsonpath, ``value`` is
    regex-escaped (so it matches literally) and then written as a JSON string
    literal, whose escaping rules jsonpath shares.
    """
    pattern = json.dumps(re.escape(value), ensure_ascii=False)
    path = f'{_SUMMARY_PATH_OPS[operator]} ? (@ like_regex {pattern} flag "i")'
    return _JsonbPathExists(F('metadata'), Value(path))


def _text_predicate(text: str) -> IContains:
    """Case- and accent-insensitive substring match on the metadata text.

    ``Unaccent`` is a bilateral transform, so Django unaccents ``text`` as
    well: ``Mäuse``, ``Mause`` and ``MAUSE`` all match each other.
    """
    return IContains(Unaccent(Cast('metadata', TextField())), text)


# A Version whose `about` holds an Anatomy entry satisfying `{condition}`, a
# condition on the entry `a`. `metadata` is left unqualified because Django
# may alias the Version table in subqueries.
_ANATOMY_SQL = """
EXISTS (
    SELECT 1
    FROM jsonb_array_elements(
        CASE WHEN jsonb_typeof(metadata->'about') = 'array'
             THEN metadata->'about' ELSE '[]'::jsonb END
    ) AS a
    WHERE a->>'schemaKey' = 'Anatomy' AND {condition}
)
"""
# The interpolated pieces are trusted constants; the value is a bound param.
_ANATOMY_BY_CURIE = _ANATOMY_SQL.format(
    condition=CURIE_SQL_TEMPLATE.format(expr="a->>'identifier'") + ' = %s'
)
_ANATOMY_BY_NAME = _ANATOMY_SQL.format(condition="a->>'name' ~* %s")


def _anatomy_predicate(value: str) -> RawSQL:
    """Match an ``anatomy_exact:`` value against the Anatomy entries in ``about``.

    An identifier (CURIE, underscore form, or IRI) matches entries with that
    identifier in any spelling. Any other value matches entries whose recorded
    name is the whole value, case-insensitively.
    """
    curie = normalize_curie(value)
    if curie is not None:
        sql, param = _ANATOMY_BY_CURIE, curie
    else:
        sql, param = _ANATOMY_BY_NAME, f'^{re.escape(value)}$'
    # `sql` is one of the two constant templates; the value is bound.
    return RawSQL(sql, [param], output_field=BooleanField())  # noqa: S611


def _owner_predicate(value: str) -> Q:
    """Match dandisets owned by the given user identifier.

    `value` is matched case-insensitively against the user's GitHub login
    (`SocialAccount.extra_data['login']` — the "username" the API and UI
    display), `User.email`, `User.first_name`, `User.last_name`, or
    `"first_name last_name"` (so the display name shown in the UI works).
    `User.username` is deliberately not matched: in production it holds the
    user's email address, not the GitHub login. Multiple users may match; we
    union dandisets owned by any of them. Unknown user → empty result.
    """
    matched_user_pks = (
        User.objects.annotate(_full_name=Concat('first_name', Value(' '), 'last_name'))
        .filter(
            Q(socialaccount__extra_data__login__iexact=value)
            | Q(email__iexact=value)
            | Q(first_name__iexact=value)
            | Q(last_name__iexact=value)
            | Q(_full_name__iexact=value)
        )
        .values_list('pk', flat=True)
    )
    owned_pks = DandisetUserObjectPermission.objects.filter(
        user__in=matched_user_pks, permission__codename='owner'
    ).values('content_object')
    return Q(pk__in=owned_pks)


# Date operator -> (what is compared, comparison). `*_before` is exclusive and
# `*_after` inclusive of the given day's midnight UTC.
_DATE_OPS = {
    'created_before': (F('created'), LessThan),
    'created_after': (F('created'), GreaterThanOrEqual),
    'modified_before': (_LATEST_VERSION_MODIFIED, LessThan),
    'modified_after': (_LATEST_VERSION_MODIFIED, GreaterThanOrEqual),
    'published_before': (_LATEST_PUBLISHED_CREATED, LessThan),
    'published_after': (_LATEST_PUBLISHED_CREATED, GreaterThanOrEqual),
}


def build_search_filter(query: str) -> Q:
    """Compile a search query into a ``Q`` for ``Dandiset.objects.filter``.

    Raises :class:`SearchSyntaxError` for queries that don't parse or that use
    an unknown operator, an empty operator value, or a malformed date.
    """
    parsed = parse_search(query)
    version_predicates = [_text_predicate(text) for text in parsed.free_text]
    dandiset_predicates = []
    for op in parsed.operators:
        if op.key in _SUMMARY_PATH_OPS:
            version_predicates.append(_summary_predicate(op.key, op.value))
        elif op.key == 'anatomy_exact':
            version_predicates.append(_anatomy_predicate(op.value))
        elif op.key in _DATE_OPS:
            lhs, lookup = _DATE_OPS[op.key]
            dandiset_predicates.append(lookup(lhs, parse_date(op.key, op.value)))
        elif op.key == 'owner':
            dandiset_predicates.append(_owner_predicate(op.value))
        else:  # pragma: no cover
            raise ValueError(f'no query for operator: {op.key}')

    q = Q(*dandiset_predicates)
    if version_predicates:
        # Filter Version in its own subquery: the unaccented-text cast and
        # jsonpath calls don't compose with the outer queryset's joins.
        matching = Version.objects.filter(*version_predicates).values('dandiset_id')
        q &= Q(id__in=matching)
    return q


def apply_search_filters(queryset: QuerySet[Dandiset], query: str) -> QuerySet[Dandiset]:
    """Restrict ``queryset`` to the dandisets matching the search query."""
    q = build_search_filter(query)
    return queryset.filter(q) if q else queryset
