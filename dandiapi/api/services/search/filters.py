"""Compile a parsed search query into a Postgres filter on the Dandiset queryset.

``build_search_filter`` walks the Lark parse tree from
:func:`~dandiapi.api.services.search.parser.parse_tree` with
``_QueryCompiler``, which turns every term into one SQL predicate:

- free text (``word`` / ``"phrase"``): case-insensitive substring match on the
  unaccented text of a version's metadata
- ``species:`` / ``approach:`` / ``technique:`` / ``standard:`` /
  ``variable:``: a ``jsonb_path_exists`` regex match on the version's
  ``assetsSummary``
- ``created_*`` / ``modified_*`` / ``published_*``: a comparison on the
  dandiset's creation time or on its latest (published) version
- ``owner:``: membership in the set of dandisets owned by matching users

Version-level predicates (free text and summary operators) are AND'd and must
all hold on a single Version row; that row's dandiset is then AND'd with the
dandiset-level predicates. The result is one ``Q`` the view applies with
``queryset.filter``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import re
from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.contrib.postgres.lookups import Unaccent
from django.db.models import BooleanField, F, Func, OuterRef, Q, Subquery, TextField, Value
from django.db.models.functions import Cast, Concat
from django.db.models.lookups import GreaterThanOrEqual, IContains, LessThan
from lark import Transformer, v_args

from dandiapi.api.models import Version
from dandiapi.api.models.dandiset import DandisetUserObjectPermission
from dandiapi.api.services.search.parser import (
    SearchSyntaxError,
    operator_from_token,
    parse_tree,
    text_from_token,
    transform_tree,
)

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from dandiapi.api.models import Dandiset
    from dandiapi.api.services.search.parser import Operator


def _latest_version_modified() -> Subquery:
    latest_version = Version.objects.filter(dandiset=OuterRef('pk')).order_by('-created')[:1]
    return Subquery(latest_version.values('modified'))


def _latest_published_created() -> Subquery:
    latest_published = (
        Version.objects.filter(dandiset=OuterRef('pk'))
        .exclude(version='draft')
        .order_by('-created')[:1]
    )
    return Subquery(latest_published.values('created'))


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
    """Case-insensitive substring match on the unaccented metadata text."""
    return IContains(Unaccent(Cast('metadata', TextField())), text)


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


def _parse_date(operator: str, value: str) -> datetime:
    try:
        return datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=UTC)
    except ValueError as exc:
        raise SearchSyntaxError(
            f'Invalid date for "{operator}": {value!r}. Use YYYY-MM-DD.'
        ) from exc


# Date operator -> (what is compared, comparison). `*_before` is exclusive and
# `*_after` inclusive of the given day's midnight UTC.
_DATE_OPS = {
    'created_before': (lambda: F('created'), LessThan),
    'created_after': (lambda: F('created'), GreaterThanOrEqual),
    'modified_before': (_latest_version_modified, LessThan),
    'modified_after': (_latest_version_modified, GreaterThanOrEqual),
    'published_before': (_latest_published_created, LessThan),
    'published_after': (_latest_published_created, GreaterThanOrEqual),
}


def _date_predicate(operator: str, value: str):
    lhs, lookup = _DATE_OPS[operator]
    return lookup(lhs(), _parse_date(operator, value))


@dataclass
class _Clause:
    """The SQL for one or more terms, split by the table it constrains.

    ``version`` predicates are evaluated against a single Version row;
    ``dandiset`` predicates against the Dandiset row.
    """

    version: list = field(default_factory=list)
    dandiset: list = field(default_factory=list)


def _compile_operator(op: Operator) -> _Clause:
    value = op.value.strip()
    if not value:
        raise SearchSyntaxError(f'Operator "{op.key}" requires a value (e.g. {op.key}:something).')
    if op.key in _SUMMARY_PATH_OPS:
        return _Clause(version=[_summary_predicate(op.key, value)])
    if op.key in _DATE_OPS:
        return _Clause(dandiset=[_date_predicate(op.key, value)])
    if op.key == 'owner':
        return _Clause(dandiset=[_owner_predicate(value)])
    raise ValueError(f'no query for operator: {op.key}')  # pragma: no cover


@v_args(inline=True)
class _QueryCompiler(Transformer):
    """Compile the search parse tree into a ``Q`` on the Dandiset queryset."""

    def quoted_operator(self, token):
        return _compile_operator(operator_from_token(token))

    bare_operator = quoted_operator

    def phrase(self, token):
        return _Clause(version=[_text_predicate(text_from_token(token))])

    word = phrase

    @v_args(inline=False)
    def start(self, clauses: list[_Clause]) -> Q:
        version_predicates = [p for c in clauses for p in c.version]
        dandiset_predicates = [p for c in clauses for p in c.dandiset]

        q = Q(*dandiset_predicates)
        if version_predicates:
            # Filter Version in its own subquery: the unaccented-text alias
            # and jsonpath calls don't compose with the outer queryset's joins.
            matching = Version.objects.filter(*version_predicates).values('dandiset_id')
            q &= Q(id__in=matching)
        return q


def build_search_filter(query: str) -> Q:
    """Compile a search query into a ``Q`` for ``Dandiset.objects.filter``.

    Raises :class:`SearchSyntaxError` for queries that don't parse or that use
    an unknown operator, an empty operator value, or a malformed date.
    """
    if not query:
        return Q()
    return transform_tree(_QueryCompiler(), parse_tree(query))


def apply_search_filters(queryset: QuerySet[Dandiset], query: str) -> QuerySet[Dandiset]:
    """Restrict ``queryset`` to the dandisets matching the search query."""
    q = build_search_filter(query)
    return queryset.filter(q) if q else queryset
