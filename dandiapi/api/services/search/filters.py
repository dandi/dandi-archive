"""Translate a ParsedSearch into Django ORM filters against the Dandiset queryset."""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.db.models import OuterRef, Q, Subquery, Value
from django.db.models.functions import Concat

from dandiapi.api.models import Version
from dandiapi.api.models.dandiset import DandisetUserObjectPermission
from dandiapi.api.services.permissions.dandiset import get_owned_dandisets
from dandiapi.api.services.search.parser import SearchSyntaxError
from dandiapi.search.models import AssetSearch

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser
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
_ASSET_OPS = frozenset({'species', 'approach', 'technique', 'standard', 'file_type'})
_OWNER_OPS = frozenset({'owner'})


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
# we want to match against. `[*]` wildcards mean we match if ANY element of
# the array satisfies the predicate — important for assets that list
# multiple species, approaches, etc. Paths MUST be trusted constants:
# they're interpolated into the SQL.
_NAME_PATH_OPS = {
    'species': '$.wasAttributedTo[*].species.name',
    'approach': '$.approach[*].name',
    'technique': '$.measurementTechnique[*].name',
    'standard': '$.dataStandard[*].name',
}


def _jsonpath_name_match(path: str, value: str) -> tuple[str, list[str]]:
    """Build a parameterized Postgres `jsonb_path_exists` predicate.

    Matches `value` case-insensitively as a substring against any node
    selected by `path`. `path` MUST come from a trusted allowlist; `value`
    is parameterized and regex-escaped.
    """
    # No table prefix on `asset_metadata`: Django may alias the AssetSearch
    # table (e.g. inside a subquery), and qualifying the column would break
    # those queries. The unqualified column is unambiguous in our usage.
    where = (
        'jsonb_path_exists(asset_metadata, '
        f"('{path} ? (@ like_regex ' "
        '|| to_jsonb(%s::text)::text || '
        '\' flag "i")\')::jsonpath)'
    )
    return where, [re.escape(value)]


def _apply_asset_filter(queryset, operator: str, value: str):
    """Apply one parsed asset operator to an AssetSearch queryset."""
    if operator in _NAME_PATH_OPS:
        where, params = _jsonpath_name_match(_NAME_PATH_OPS[operator], value)
        # `where` interpolates only an allowlisted jsonpath; the user value
        # is bound via params (and re-escaped against regex injection).
        return queryset.extra(where=[where], params=params)  # noqa: S610
    if operator == 'file_type':
        mime_prefix = _FILE_TYPE_ALIASES.get(value.lower(), value)
        return queryset.filter(asset_metadata__encodingFormat__istartswith=mime_prefix)
    raise ValueError(f'unknown asset operator: {operator}')  # pragma: no cover


def _apply_owner_filter(
    queryset: QuerySet[Dandiset], value: str, *, request_user: User | AnonymousUser
) -> QuerySet[Dandiset]:
    """Filter dandisets to those owned by the given user identifier.

    `owner:me` resolves to the requesting user; otherwise we match `value`
    case-insensitively against:
      - User.username
      - User.email
      - User.first_name
      - User.last_name
      - "first_name last_name"  (so the display name shown in the UI works)

    Multiple users may match (common when only a first or last name is given);
    we union dandisets owned by any of them. Unknown user → empty result (not
    an error — a search for a nonexistent owner is a valid 0-hit query).

    Direct query against `DandisetUserObjectPermission` rather than guardian's
    `get_objects_for_user` so we can intersect across multiple matched users
    in a single query, and to bypass the superuser-sees-everything default.
    """
    if value.lower() == 'me':
        if request_user.is_anonymous:
            raise SearchSyntaxError(
                'owner:me requires authentication. Sign in or specify a username.'
            )
        owner_pks = get_owned_dandisets(request_user, include_superusers=False).values('pk')
        return queryset.filter(pk__in=owner_pks)

    matched_user_pks = (
        User.objects.annotate(_full_name=Concat('first_name', Value(' '), 'last_name'))
        .filter(
            Q(username__iexact=value)
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
        elif key in _ASSET_OPS:
            if asset_qs is None:
                asset_qs = AssetSearch.objects.visible_to(user)
            asset_qs = _apply_asset_filter(asset_qs, key, value)
        elif key in _OWNER_OPS:
            queryset = _apply_owner_filter(queryset, value, request_user=user)

    if asset_qs is not None:
        # NOTE perf: jsonb_path_exists with a runtime-built jsonpath cannot
        # use the existing per-field GIN indexes; the path-scan operators
        # (species/approach/technique/standard) currently sequential-scan the
        # asset_search materialized view. The view is small enough today
        # (~one row per asset) that this is acceptable, but if it becomes a
        # hot path the fix is expression GIN indexes on each path or
        # denormalized text columns + trgm_ops indexes.
        matching_dandiset_ids = asset_qs.values_list('dandiset_id', flat=True).distinct()
        queryset = queryset.filter(id__in=matching_dandiset_ids)

    return queryset
