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
_ASSET_OPS = frozenset({'species', 'approach', 'technique', 'file_type'})


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


# Each entry maps an operator to a Postgres jsonpath that selects the names
# we want to match against, within an asset's metadata. `[*]` wildcards mean
# we match if ANY element of the array satisfies the predicate — important for
# assets that list multiple species, approaches, etc. Paths MUST be trusted
# constants: they're interpolated into the SQL.
_NAME_PATH_OPS = {
    'species': '$.wasAttributedTo[*].species.name',
    'approach': '$.approach[*].name',
    'technique': '$.measurementTechnique[*].name',
}

# The data standard is reported on the Version's `assetsSummary`, not on
# individual assets, so it's matched against the Version metadata column rather
# than the asset_search view.
_STANDARD_PATH = '$.assetsSummary.dataStandard[*].name'


def _jsonpath_name_match(column: str, path: str, value: str) -> tuple[str, list[str]]:
    """Build a parameterized Postgres `jsonb_path_exists` predicate.

    Matches `value` case-insensitively as a substring against any node
    selected by `path` within `column`. Both `column` and `path` MUST come
    from a trusted allowlist; `value` is parameterized and regex-escaped.
    """
    # No table prefix on the column: Django may alias the table (e.g. inside a
    # subquery), and qualifying the column would break those queries. The
    # unqualified column is unambiguous in our usage.
    where = (
        f'jsonb_path_exists({column}, '
        f"('{path} ? (@ like_regex ' "
        '|| to_jsonb(%s::text)::text || '
        '\' flag "i")\')::jsonpath)'
    )
    return where, [re.escape(value)]


def _apply_asset_filter(queryset, operator: str, value: str):
    """Apply one parsed asset operator to an AssetSearch queryset."""
    if operator in _NAME_PATH_OPS:
        where, params = _jsonpath_name_match('asset_metadata', _NAME_PATH_OPS[operator], value)
        # `where` interpolates only an allowlisted jsonpath; the user value
        # is bound via params (and re-escaped against regex injection).
        return queryset.extra(where=[where], params=params)  # noqa: S610
    if operator == 'file_type':
        mime_prefix = _FILE_TYPE_ALIASES.get(value.lower(), value)
        return queryset.filter(asset_metadata__encodingFormat__istartswith=mime_prefix)
    raise ValueError(f'unknown asset operator: {operator}')  # pragma: no cover


def _apply_standard_filter(queryset, value: str):
    """Filter dandisets whose version assetsSummary lists a matching data standard.

    Unlike the asset operators, `dataStandard` lives on the Version metadata
    (`assetsSummary.dataStandard`), so we match against Versions and restrict the
    dandiset queryset to those that have at least one matching version.
    """
    where, params = _jsonpath_name_match('metadata', _STANDARD_PATH, value)
    matching_dandiset_ids = (
        Version.objects.extra(where=[where], params=params)  # noqa: S610
        .values_list('dandiset_id', flat=True)
        .distinct()
    )
    return queryset.filter(id__in=matching_dandiset_ids)


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

    # `asset_qs` is built lazily so a query with no asset ops pays nothing.
    # Note on semantics: chaining `.filter()` AND's the conditions on a SINGLE
    # AssetSearch row, so e.g. `species:mouse approach:ephys` returns dandisets
    # with at least one asset that satisfies BOTH (cross-key AND on the same
    # asset). Repeated keys (`species:mouse species:rat`) likewise require a
    # single asset to match both substrings — same as GitHub's default.
    asset_qs = None
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
        elif key == 'standard':
            queryset = _apply_standard_filter(queryset, value)
        elif key in _ASSET_OPS:
            if asset_qs is None:
                asset_qs = AssetSearch.objects.visible_to(user)
            asset_qs = _apply_asset_filter(asset_qs, key, value)

    if asset_qs is not None:
        # NOTE perf: jsonb_path_exists with a runtime-built jsonpath cannot
        # use the existing per-field GIN indexes; the path-scan operators
        # (species/approach/technique) currently sequential-scan the
        # asset_search materialized view. The view is small enough today
        # (~one row per asset) that this is acceptable, but if it becomes a
        # hot path the fix is expression GIN indexes on each path or
        # denormalized text columns + trgm_ops indexes.
        matching_dandiset_ids = asset_qs.values_list('dandiset_id', flat=True).distinct()
        queryset = queryset.filter(id__in=matching_dandiset_ids)

    return queryset
