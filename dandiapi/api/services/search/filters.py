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
    CONTRIBUTOR_ROLE_OPS,
    DATE_OPS,
    OWNER_OPS,
    SUMMARY_PATH_OPS,
)
from dandiapi.api.services.search.parser import SearchSyntaxError

if TYPE_CHECKING:
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
        where, params = _jsonpath_match(SUMMARY_PATH_OPS[operator], value)
        # `where` interpolates only an allowlisted jsonpath; the user value
        # is bound via params (and regex-escaped).
        version_qs = version_qs.extra(where=[where], params=params)  # noqa: S610
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


def apply_search_filters(  # noqa: C901  (one branch per operator category — splitting the dispatch loop wouldn't make it more readable)
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
    annotated: set[str] = set()
    # Contributor predicates apply to a single Version's
    # metadata.contributor[] array, so we accumulate them and AND on the same
    # Version to avoid cross-version weirdness when a draft and a published
    # version have disjoint contributor lists. Within that single version
    # each predicate independently scans `contributor[*]`, so two operators
    # may match different contributor entries.
    contributor_wheres: list[tuple[str, list[str]]] = []

    for op in parsed.operators:
        key = op.key
        value = op.value.strip()
        if not value:
            raise SearchSyntaxError(f'Operator "{key}" requires a value (e.g. {key}:something).')

        if key in DATE_OPS:
            queryset = _apply_date_filter(queryset, key, _parse_date(key, value), annotated)
        elif key in SUMMARY_PATH_OPS:
            summary_clauses.append((key, value))
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

    if summary_clauses:
        queryset = _apply_summary_filters(queryset, summary_clauses)

    return queryset
