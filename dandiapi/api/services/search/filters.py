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
from dandiapi.api.services.search.operators import (
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


# Postgres jsonpath quirk: `like_regex` requires its pattern to be a STRING
# LITERAL inside the jsonpath text, not a `$variable`, so the `vars` argument
# of `jsonb_path_exists` can't carry the pattern. Instead the jsonpath is
# assembled at execution time by concatenating `to_jsonb(%s::text)::text`,
# which renders the bound parameter as a properly quoted JSON string literal.
# The user value is never inlined into the SQL, and callers `re.escape` it so
# regex metacharacters match literally.
_LIKE_REGEX_PATTERN = ' like_regex \' || to_jsonb(%s::text)::text || \' flag "i"'


def _jsonpath_match(path: str, value: str) -> tuple[str, list[str]]:
    """Build a parameterized `jsonb_path_exists` predicate on `metadata`.

    `path` MUST come from a trusted allowlist; `value` is parameterized and
    regex-escaped.
    """
    # `metadata` is left unqualified because Django may alias the Version
    # table in subqueries.
    where = f"jsonb_path_exists(metadata, ('{path} ? (@{_LIKE_REGEX_PATTERN})')::jsonpath)"
    return where, [re.escape(value)]


def _apply_version_filters(
    queryset: QuerySet[Dandiset], wheres: list[tuple[str, list[str]]]
) -> QuerySet[Dandiset]:
    """Restrict dandisets to those with a version whose metadata satisfies every predicate.

    `wheres` is a list of `(where_clause, params)` pairs, one per operator,
    from `_jsonpath_match`, `_contributor_where`, or `_affiliation_where`.
    All predicates are AND'd on a single Version row, so a draft and a
    published version never combine into a spurious match. Filtering by
    `id__in` over distinct dandiset ids (instead of joining `versions`) keeps
    each dandiset to one row even when several of its versions match.
    """
    version_qs = Version.objects.all()
    for where, params in wheres:
        # `where` interpolates only allowlisted jsonpath text; the user value
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


def _contributor_where(value: str, role: str | None) -> tuple[str, list[str]]:
    """Build a `jsonb_path_exists(metadata, ...)` where clause for a contributor[] predicate.

    Matches a `contributor[]` element whose `name`, `email`, OR `identifier`
    contains `value` (case-insensitive). If `role` is given, additionally
    requires that element's `roleName` array to contain exactly
    `dcite:<role>` (case-insensitive).
    """
    val_clause = (
        f'@.name{_LIKE_REGEX_PATTERN}'
        f' || @.email{_LIKE_REGEX_PATTERN}'
        f' || @.identifier{_LIKE_REGEX_PATTERN}'
    )
    params = [re.escape(value)] * 3
    if role is None:
        jsonpath_expr = f"'$.contributor[*] ? ({val_clause})'"
    else:
        jsonpath_expr = (
            f"'$.contributor[*] ? (({val_clause})"
            f" && exists(@.roleName[*] ? (@{_LIKE_REGEX_PATTERN})))'"
        )
        # Anchored so `author:` can't also match a future `dcite:CoAuthor`.
        params.append(f'^dcite:{re.escape(role)}$')
    where = f'jsonb_path_exists(metadata, ({jsonpath_expr})::jsonpath)'
    return where, params


def _affiliation_where(value: str) -> tuple[str, list[str]]:
    """Build a `jsonb_path_exists(metadata, ...)` where clause for the affiliation predicate.

    Affiliations live at `contributor[].affiliation[]`, each with a `name` and
    optionally an `identifier` (ROR URL). Matches case-insensitive substring
    on either.
    """
    clause = f'@.name{_LIKE_REGEX_PATTERN} || @.identifier{_LIKE_REGEX_PATTERN}'
    where = (
        f"jsonb_path_exists(metadata, ('$.contributor[*].affiliation[*] ? ({clause})')::jsonpath)"
    )
    return where, [re.escape(value)] * 2


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

    annotated: set[str] = set()
    # Metadata predicates (assetsSummary, contributor, affiliation) are
    # accumulated and AND'd on the same Version, so a draft and a published
    # version with different metadata never combine into a spurious match.
    # Within that version each contributor predicate independently scans
    # `contributor[*]`, so two operators may match different contributors.
    version_wheres: list[tuple[str, list[str]]] = []

    for op in parsed.operators:
        key = op.key
        value = op.value.strip()
        if not value:
            raise SearchSyntaxError(f'Operator "{key}" requires a value (e.g. {key}:something).')

        if key in DATE_OPS:
            queryset = _apply_date_filter(queryset, key, _parse_date(key, value), annotated)
        elif key in SUMMARY_PATH_OPS:
            version_wheres.append(_jsonpath_match(SUMMARY_PATH_OPS[key], value))
        elif key in OWNER_OPS:
            queryset = _apply_owner_filter(queryset, value)
        elif key in CONTRIBUTOR_ROLE_OPS:
            version_wheres.append(_contributor_where(value, CONTRIBUTOR_ROLE_OPS[key]))
        elif key in AFFILIATION_OPS:
            version_wheres.append(_affiliation_where(value))

    if version_wheres:
        queryset = _apply_version_filters(queryset, version_wheres)

    return queryset
