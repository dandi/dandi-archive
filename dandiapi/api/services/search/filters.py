"""Translate a ParsedSearch into Django ORM filters against the Dandiset queryset."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import re
from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.db.models import OuterRef, Q, Subquery, Value
from django.db.models.functions import Concat

from dandiapi.api.models import Version
from dandiapi.api.models.dandiset import DandisetUserObjectPermission
from dandiapi.api.services.search.operators import (
    AFFILIATION_JSONPATH,
    AFFILIATION_OPS,
    ASSET_NAME_PATH_OPS,
    ASSET_OPS,
    CONTRIBUTOR_ROLE_OPS,
    DATE_OPS,
    FILE_TYPE_ALIASES,
    OWNER_OPS,
)
from dandiapi.api.services.search.parser import SearchSyntaxError
from dandiapi.search.models import AssetSearch

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser
    from django.db.models import QuerySet

    from dandiapi.api.models import Dandiset
    from dandiapi.api.services.search.parser import ParsedSearch


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


def _jsonpath_name_match(path: str, value: str) -> tuple[str, list[str]]:
    """Asset-metadata jsonpath substring predicate; `path` must be trusted."""
    where = (
        'jsonb_path_exists(asset_metadata, '
        f"('{path} ? (@ like_regex ' "
        '|| to_jsonb(%s::text)::text || '
        '\' flag "i")\')::jsonpath)'
    )
    return where, [re.escape(value)]


def _apply_asset_filter(queryset, operator: str, value: str):
    """Apply one parsed asset operator to an AssetSearch queryset."""
    if operator in ASSET_NAME_PATH_OPS:
        where, params = _jsonpath_name_match(ASSET_NAME_PATH_OPS[operator], value)
        return queryset.extra(where=[where], params=params)  # noqa: S610
    if operator == 'file_type':
        mime_prefix = FILE_TYPE_ALIASES.get(value.lower(), value)
        return queryset.filter(asset_metadata__encodingFormat__istartswith=mime_prefix)
    raise ValueError(f'unknown asset operator: {operator}')  # pragma: no cover


def _apply_owner_filter(queryset: QuerySet[Dandiset], value: str) -> QuerySet[Dandiset]:
    """Filter dandisets to those owned by users matching `value` (icontains)."""
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


def _contributor_role_jsonpath(value: str, role: str | None) -> tuple[str, dict[str, str]]:
    """Jsonpath + vars for a contributor[] predicate (optional role constraint)."""
    name_or_email_or_id = (
        '@.name like_regex $val flag "i" '
        ' || @.email like_regex $val flag "i" '
        ' || @.identifier like_regex $val flag "i"'
    )
    if role is None:
        return f'$.contributor[*] ? ({name_or_email_or_id})', {'val': re.escape(value)}
    return (
        '$.contributor[*] ? '
        f'(({name_or_email_or_id}) '
        '  && exists(@.roleName[*] ? (@ like_regex $role flag "i")))',
        {'val': re.escape(value), 'role': re.escape(role)},
    )


def _build_jsonpath_where(jsonpath: str, vars_obj: dict[str, str]) -> tuple[str, list[str]]:
    """Wrap a jsonpath + vars into a `jsonb_path_exists(metadata, ...)` predicate."""
    where = f"jsonb_path_exists(metadata, '{jsonpath}'::jsonpath, %s::jsonb)"
    return where, [json.dumps(vars_obj)]


def _apply_contributor_filters(
    queryset: QuerySet[Dandiset], wheres: list[tuple[str, list[str]]]
) -> QuerySet[Dandiset]:
    """Filter dandisets by accumulated contributor predicates.

    `wheres` is a list of `(where_clause, params)` pairs (one per operator).
    The returned queryset is restricted to dandisets that have at least ONE
    Version whose `metadata` satisfies ALL the predicates simultaneously.
    Operators thus AND on the same Version (a draft and a published version
    with disjoint contributor lists never combine into a spurious match).

    Each operator is independent: `author:Doe funder:NIH` matches if SOME
    contributor element has Doe as Author AND SOME contributor element (the
    same OR a different one) has NIH as Funder.
    """
    matching_versions = Version.objects.all()
    for where, params in wheres:
        # Trusted jsonpath template (no user value interpolated); user value
        # is bound via the jsonb vars param and additionally regex-escaped.
        matching_versions = matching_versions.extra(  # noqa: S610
            where=[where], params=params
        )
    return queryset.filter(versions__pk__in=matching_versions.values('pk'))


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


def apply_search_filters(  # noqa: C901  (one branch per operator category — splitting the dispatch loop wouldn't make it more readable)
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
    # Contributor predicates collected here, then applied in a single batch so
    # all operators AND on the same Version (avoids cross-version weirdness
    # when a dandiset has both a draft and a published version with disjoint
    # contributor lists).
    contributor_wheres: list[tuple[str, list[str]]] = []

    for op in parsed.operators:
        key = op.key
        value = op.value.strip()
        if not value:
            raise SearchSyntaxError(f'Operator "{key}" requires a value (e.g. {key}:something).')

        if key in DATE_OPS:
            try:
                ts = datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=UTC)
            except ValueError as exc:
                raise SearchSyntaxError(
                    f'Invalid date for "{key}": {value!r}. Use YYYY-MM-DD.'
                ) from exc
            queryset = _apply_date_filter(queryset, key, ts, annotated)
        elif key in ASSET_OPS:
            if asset_qs is None:
                asset_qs = AssetSearch.objects.visible_to(user)
            asset_qs = _apply_asset_filter(asset_qs, key, value)
        elif key in OWNER_OPS:
            queryset = _apply_owner_filter(queryset, value)
        elif key in CONTRIBUTOR_ROLE_OPS:
            jsonpath, vars_obj = _contributor_role_jsonpath(value, CONTRIBUTOR_ROLE_OPS[key])
            contributor_wheres.append(_build_jsonpath_where(jsonpath, vars_obj))
        elif key in AFFILIATION_OPS:
            contributor_wheres.append(
                _build_jsonpath_where(AFFILIATION_JSONPATH, {'val': re.escape(value)})
            )

    if contributor_wheres:
        queryset = _apply_contributor_filters(queryset, contributor_wheres)

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
