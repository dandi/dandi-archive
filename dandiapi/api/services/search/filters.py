"""Translate a ParsedSearch into Django ORM filters against the Dandiset queryset."""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import TYPE_CHECKING

from django.db.models import OuterRef, Subquery

from dandiapi.api.models import Version
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
_ASSET_OPS = frozenset(
    {'has_species', 'has_approach', 'has_technique', 'has_standard', 'has_file_type'}
)


def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=UTC)
    except ValueError:
        return None


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


_NAME_ARRAY_FIELDS = {
    'has_approach': 'approach',
    'has_technique': 'measurementTechnique',
    'has_standard': 'dataStandard',
}


def _name_array_jsonpath(field: str, value: str) -> tuple[str, list[str]]:
    """Build a parameterized Postgres `jsonb_path_exists` predicate.

    Matches case-insensitively against the `.name` of *any* element of the
    asset_metadata.<field> JSON array. `field` MUST come from a trusted
    allowlist (it's interpolated into the SQL); `value` is parameterized.
    """
    # No table prefix on `asset_metadata`: Django may alias the AssetSearch
    # table (e.g. inside a subquery), and qualifying the column would break
    # those queries. The unqualified column is unambiguous in our usage.
    where = (
        'jsonb_path_exists(asset_metadata, '
        f'(\'$."{field}"[*].name ? (@ like_regex \' '
        '|| to_jsonb(%s::text)::text || \' flag "i")\')::jsonpath)'
    )
    return where, [re.escape(value)]


def _apply_asset_filter(queryset, operator: str, value: str):
    """Apply one parsed asset operator to an AssetSearch queryset."""
    if operator == 'has_species':
        return queryset.filter(species__icontains=value)
    if operator in _NAME_ARRAY_FIELDS:
        where, params = _name_array_jsonpath(_NAME_ARRAY_FIELDS[operator], value)
        # `where` interpolates only an allowlisted field name; the user value
        # is bound via params (and re-escaped against regex injection).
        return queryset.extra(where=[where], params=params)  # noqa: S610
    if operator == 'has_file_type':
        mime_prefix = _FILE_TYPE_ALIASES.get(value.lower(), value)
        return queryset.filter(asset_metadata__encodingFormat__istartswith=mime_prefix)
    raise ValueError(f'unknown asset operator: {operator}')  # pragma: no cover


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

    asset_qs = None  # built lazily so a query with no asset ops pays nothing
    annotated: set[str] = set()

    for key, raw_value in parsed.operators:
        value = raw_value.strip()
        if not value:
            continue

        if key in _DATE_OPS:
            if (ts := _parse_date(value)) is None:
                # Malformed date — fail closed (return nothing) rather than
                # silently dropping the filter and returning everything.
                return queryset.none()
            queryset = _apply_date_filter(queryset, key, ts, annotated)
        elif key in _ASSET_OPS:
            if asset_qs is None:
                asset_qs = AssetSearch.objects.visible_to(user)
            asset_qs = _apply_asset_filter(asset_qs, key, value)

    if asset_qs is not None:
        matching_dandiset_ids = asset_qs.values_list('dandiset_id', flat=True).distinct()
        queryset = queryset.filter(id__in=matching_dandiset_ids)

    return queryset
