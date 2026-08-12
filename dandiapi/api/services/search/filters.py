"""Translate a ParsedSearch into Django ORM filters against the Dandiset queryset."""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import TYPE_CHECKING

from django.db.models import OuterRef, Subquery

from dandiapi.api.models import Version
from dandiapi.api.services.search.parser import SearchSyntaxError
from dandiapi.search.models import AssetSearch

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User
    from django.db.models import QuerySet

    from dandiapi.api.models import Dandiset
    from dandiapi.api.services.search.parser import ParsedSearch

# Aliases for the file-type operator: short name → MIME prefix matched with
# istartswith. Keep in sync with DandisetSearchQueryParameterSerializer.
_FILE_TYPE_ALIASES = {
    'nwb': 'application/x-nwb',
    'image': 'image/',
    'text': 'text/',
    'video': 'video/',
}

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
_ASSET_OPS = frozenset({'file_type'})


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
# interpolated into the SQL.
_SUMMARY_PATH_OPS = {
    'species': '$.assetsSummary.species[*].name',
    'approach': '$.assetsSummary.approach[*].name',
    'technique': '$.assetsSummary.measurementTechnique[*].name',
}


def _jsonpath_name_match(path: str, value: str) -> tuple[str, list[str]]:
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
        where, params = _jsonpath_name_match(_SUMMARY_PATH_OPS[operator], value)
        # `where` interpolates only an allowlisted jsonpath; the user value
        # is bound via params (and regex-escaped).
        version_qs = version_qs.extra(where=[where], params=params)  # noqa: S610
    return queryset.filter(id__in=version_qs.values_list('dandiset_id', flat=True).distinct())


def _apply_file_type_filters(
    queryset: QuerySet[Dandiset], values: list[str], user: User | AnonymousUser
) -> QuerySet[Dandiset]:
    """Restrict dandisets to those with an asset matching every file_type value."""
    asset_qs = AssetSearch.objects.visible_to(user)
    for value in values:
        mime_prefix = _FILE_TYPE_ALIASES.get(value.lower(), value)
        asset_qs = asset_qs.filter(asset_metadata__encodingFormat__istartswith=mime_prefix)
    return queryset.filter(id__in=asset_qs.values_list('dandiset_id', flat=True).distinct())


_MODIFIED_ALIAS = '_search_latest_version_modified'
_PUBLISHED_ALIAS = '_search_latest_published_created'


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
    *,
    user: User | AnonymousUser,
) -> QuerySet[Dandiset]:
    """Apply structured operator filters onto a Dandiset queryset.

    Free text in ``parsed`` is *not* applied here — that stays in the existing
    full-text filter so the two paths can be tested independently.
    """
    if not parsed.operators:
        return queryset

    summary_clauses: list[tuple[str, str]] = []
    file_type_values: list[str] = []
    annotated: set[str] = set()

    for key, raw_value in parsed.operators:
        value = raw_value.strip()
        if not value:
            raise SearchSyntaxError(f'Operator "{key}" requires a value (e.g. {key}:something).')

        if key in _DATE_OPS:
            try:
                ts = datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=UTC)
            except ValueError as exc:
                raise SearchSyntaxError(
                    f'Invalid date for "{key}": {value!r}. Use YYYY-MM-DD.'
                ) from exc
            queryset = _apply_date_filter(queryset, key, ts, annotated)
        elif key in _SUMMARY_PATH_OPS:
            summary_clauses.append((key, value))
        elif key in _ASSET_OPS:
            file_type_values.append(value)

    if summary_clauses:
        queryset = _apply_summary_filters(queryset, summary_clauses)

    if file_type_values:
        queryset = _apply_file_type_filters(queryset, file_type_values, user)

    return queryset
