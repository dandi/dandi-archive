"""Translate a ParsedSearch into Django ORM filters against the Dandiset queryset."""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.db import connection
from django.db.models import OuterRef, Q, Subquery, Value
from django.db.models.functions import Concat

from dandiapi.api.models import Version
from dandiapi.api.models.dandiset import DandisetUserObjectPermission
from dandiapi.api.services.search.anatomy import CURIE_SQL_TEMPLATE, normalize_curie
from dandiapi.api.services.search.parser import SearchSyntaxError
from dandiapi.search.ontology import anatomy_ontology

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from dandiapi.api.models import Dandiset
    from dandiapi.api.services.search.parser import ParsedSearch

_DATE_OPS = frozenset(
    {
        'created_before',
        'created_after',
        'modified_before',
        'modified_after',
        'published_before',
        'published_after',
    }
)
_OWNER_OPS = frozenset({'owner'})
_ANATOMY_OPS = frozenset({'anatomy', 'anatomy_exact'})


def _annotate_latest_version_modified(queryset):
    latest_version = Version.objects.filter(dandiset=OuterRef('pk')).order_by('-created')[:1]
    return queryset.annotate(
        _search_latest_version_modified=Subquery(latest_version.values('modified'))
    )


def _annotate_latest_published_created(queryset):
    latest_published = (
        Version.objects.filter(dandiset=OuterRef('pk'))
        .exclude(version='draft')
        .order_by('-created')[:1]
    )
    return queryset.annotate(
        _search_latest_published_created=Subquery(latest_published.values('created'))
    )


# Maps each operator to a Postgres jsonpath into the version-level
# `assetsSummary` aggregation. Paths MUST be trusted constants: they're
# interpolated into the SQL. `variableMeasured` holds bare strings rather
# than objects with a `name`, so its path selects the elements themselves.
_SUMMARY_PATH_OPS = {
    'species': '$.assetsSummary.species[*].name',
    'approach': '$.assetsSummary.approach[*].name',
    'technique': '$.assetsSummary.measurementTechnique[*].name',
    'standard': '$.assetsSummary.dataStandard[*].name',
    'variable': '$.assetsSummary.variableMeasured[*]',
}


def _jsonpath_match(path: str, value: str) -> tuple[str, list[str]]:
    """Build a parameterized `jsonb_path_exists` predicate on `metadata`.

    `path` MUST come from a trusted allowlist; `value` is parameterized and
    regex-escaped.
    """
    # `metadata` is left unqualified because Django may alias the Version
    # table in subqueries.
    where = (
        'jsonb_path_exists(metadata, '
        f"('{path} ? (@ like_regex ' "
        '|| to_jsonb(%s::text)::text || '
        '\' flag "i")\')::jsonpath)'
    )
    return where, [re.escape(value)]


def _apply_summary_filters(
    queryset: QuerySet[Dandiset], clauses: list[tuple[str, str]]
) -> QuerySet[Dandiset]:
    """Restrict dandisets to those with a version whose assetsSummary matches every clause.

    Clauses are AND'd on a single Version row.
    """
    version_qs = Version.objects.all()
    for operator, value in clauses:
        where, params = _jsonpath_match(_SUMMARY_PATH_OPS[operator], value)
        # `where` interpolates only an allowlisted jsonpath; the user value
        # is bound via params (and regex-escaped).
        version_qs = version_qs.extra(where=[where], params=params)  # noqa: S610
    return queryset.filter(id__in=version_qs.values_list('dandiset_id', flat=True).distinct())


# The Anatomy entries of a Version's `about`, as rows `a`. `metadata` is left
# unqualified because Django may alias the Version table in subqueries.
_ANATOMY_ENTRIES = """
jsonb_array_elements(
    CASE WHEN jsonb_typeof(metadata->'about') = 'array'
         THEN metadata->'about' ELSE '[]'::jsonb END
) AS a
"""
_ANATOMY_CURIE_SQL = CURIE_SQL_TEMPLATE.format(expr="a->>'identifier'")

# Matches a Version that holds an Anatomy entry with one of the given CURIEs, or
# whose id is one of the given ids. The interpolated pieces are trusted
# constants; every user-derived value is bound via params.
_ANATOMY_WHERE = f"""
EXISTS (
    SELECT 1 FROM {_ANATOMY_ENTRIES}
    WHERE a->>'schemaKey' = 'Anatomy' AND {_ANATOMY_CURIE_SQL} = ANY(%s::text[])
)
OR id = ANY(%s::bigint[])
"""  # noqa: S608

# Every Anatomy entry whose recorded name matches a regex, with its CURIE.
_ANATOMY_NAMES_SQL = f"""
SELECT id, {_ANATOMY_CURIE_SQL}
FROM {Version._meta.db_table}, {_ANATOMY_ENTRIES}
WHERE a->>'schemaKey' = 'Anatomy' AND a->>'name' ~* %s
"""  # noqa: S608


def _name_regex(value: str, *, whole: bool) -> str:
    """Build a Postgres regex matching `value` as the whole name, or as whole words in it."""
    if whole:
        return f'^{re.escape(value)}$'
    return f'(^|[^[:alnum:]]){re.escape(value)}($|[^[:alnum:]])'


def _versions_matching_name(pattern: str) -> list[int]:
    """Return the Versions with an Anatomy entry named like `pattern` and no known identifier.

    An entry with an identifier the ontology knows is judged by that identifier
    alone, so a CA1 entry whose name mentions the cortex is not a cortex hit.
    """
    ontology = anatomy_ontology()
    with connection.cursor() as cursor:
        cursor.execute(_ANATOMY_NAMES_SQL, [pattern])
        return sorted({version_id for version_id, curie in cursor if curie not in ontology})


def _anatomy_params(value: str, *, expand: bool) -> list:
    """Resolve an anatomy operator value into the params of `_ANATOMY_WHERE`.

    An identifier (CURIE, underscore form, or IRI) is matched as that term. Any
    other value is looked up as a label or synonym, exactly first and then by
    substring, and is also matched against the recorded `name` so that entries
    with no usable identifier, or an install without the ontology, still work.
    With `expand`, every term is widened to everything it contains.
    """
    ontology = anatomy_ontology()
    curie = normalize_curie(value)
    if curie is not None:
        terms = {curie}
        version_ids = []
    else:
        terms = ontology.find(value)
        # Without expansion the recorded name has to be the whole value, or
        # "hippocampus" would still pick up "CA1 field of hippocampus".
        version_ids = _versions_matching_name(_name_regex(value, whole=not expand))

    if expand:
        terms = set().union(*(ontology.descendants(term) for term in terms))
    return [sorted(terms), version_ids]


def _apply_anatomy_filters(
    queryset: QuerySet[Dandiset], clauses: list[tuple[str, str]]
) -> QuerySet[Dandiset]:
    """Restrict dandisets to those with a version whose `about` anatomy matches every clause."""
    version_qs = Version.objects.all()
    for operator, value in clauses:
        params = _anatomy_params(value, expand=operator == 'anatomy')
        version_qs = version_qs.extra(where=[_ANATOMY_WHERE], params=params)  # noqa: S610
    return queryset.filter(id__in=version_qs.values_list('dandiset_id', flat=True).distinct())


def _apply_owner_filter(queryset: QuerySet[Dandiset], value: str) -> QuerySet[Dandiset]:
    """Filter dandisets to those owned by the given user identifier.

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
    return queryset.filter(pk__in=owned_pks)


_MODIFIED_ALIAS = '_search_latest_version_modified'
_PUBLISHED_ALIAS = '_search_latest_published_created'


def _parse_date(operator: str, value: str) -> datetime:
    try:
        return datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=UTC)
    except ValueError as exc:
        raise SearchSyntaxError(
            f'Invalid date for "{operator}": {value!r}. Use YYYY-MM-DD.'
        ) from exc


def _apply_date_filter(queryset, operator: str, ts: datetime, annotated: set[str]):
    """Apply a single parsed date operator to the queryset, annotating as needed.

    ``annotated`` is mutated to track which annotation aliases have been added,
    so repeated date operators (e.g. modified_before AND modified_after) don't
    re-annotate the queryset and conflict.
    """
    if operator == 'created_before':
        return queryset.filter(created__lt=ts)
    if operator == 'created_after':
        return queryset.filter(created__gte=ts)
    if operator in {'modified_before', 'modified_after'}:
        if _MODIFIED_ALIAS not in annotated:
            queryset = _annotate_latest_version_modified(queryset)
            annotated.add(_MODIFIED_ALIAS)
        suffix = '__lt' if operator == 'modified_before' else '__gte'
        return queryset.filter(**{_MODIFIED_ALIAS + suffix: ts})
    if operator in {'published_before', 'published_after'}:
        if _PUBLISHED_ALIAS not in annotated:
            queryset = _annotate_latest_published_created(queryset)
            annotated.add(_PUBLISHED_ALIAS)
        suffix = '__lt' if operator == 'published_before' else '__gte'
        return queryset.filter(**{_PUBLISHED_ALIAS + suffix: ts})
    raise ValueError(f'unknown date operator: {operator}')  # pragma: no cover


def apply_search_filters(
    queryset: QuerySet[Dandiset],
    parsed: ParsedSearch,
) -> QuerySet[Dandiset]:
    """Apply structured operator filters onto a Dandiset queryset.

    Free text in ``parsed`` is *not* applied here — that stays in the existing
    full-text filter so the two paths can be tested independently.
    """
    if not parsed.operators:
        return queryset

    summary_clauses: list[tuple[str, str]] = []
    anatomy_clauses: list[tuple[str, str]] = []
    annotated: set[str] = set()

    for op in parsed.operators:
        key = op.key
        value = op.value.strip()
        if not value:
            raise SearchSyntaxError(f'Operator "{key}" requires a value (e.g. {key}:something).')

        if key in _DATE_OPS:
            queryset = _apply_date_filter(queryset, key, _parse_date(key, value), annotated)
        elif key in _SUMMARY_PATH_OPS:
            summary_clauses.append((key, value))
        elif key in _OWNER_OPS:
            queryset = _apply_owner_filter(queryset, value)
        elif key in _ANATOMY_OPS:
            anatomy_clauses.append((key, value))

    if summary_clauses:
        queryset = _apply_summary_filters(queryset, summary_clauses)

    if anatomy_clauses:
        queryset = _apply_anatomy_filters(queryset, anatomy_clauses)

    return queryset
