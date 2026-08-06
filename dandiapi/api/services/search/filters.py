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
    AFFILIATION_OPS,
    ASSET_NAME_PATH_OPS,
    ASSET_OPS,
    CONTRIBUTOR_ROLE_OPS,
    COUNT_OPS,
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
    """Filter dandisets to those owned by users matching `value` (iexact)."""
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


# Postgres jsonpath quirk: `like_regex` requires its pattern to be a STRING
# LITERAL inside the jsonpath text — not a `$variable`. So we can't use the
# `vars` arg of `jsonb_path_exists` for the regex pattern; we have to build
# the jsonpath at SQL execution time by concatenating `to_jsonb(?::text)::text`
# (a properly-quoted JSON string literal) into the path. The user value is
# still bound as a parameter — never inlined into the SQL — so the value
# remains SQL-injection-safe. `re.escape` neutralizes regex metachars.
_LIKE_REGEX_PATTERN = ' like_regex \' || to_jsonb(%s::text)::text || \' flag "i"'


def _contributor_where(value: str, role: str | None) -> tuple[str, list[str]]:
    """Build a `jsonb_path_exists(metadata, ...)` where clause for a contributor[] predicate.

    Matches a `contributor[]` element whose `name`, `email`, OR `identifier`
    contains `value` (case-insensitive). If `role` is given, additionally
    requires that element's `roleName` array to contain a string matching
    `role` (also case-insensitive substring).
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
        params.append(re.escape(role))
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


# Comparator prefix → Postgres jsonpath operator. The keys are the syntax we
# accept in a count value (`num_subjects:>=10`); the values are the jsonpath
# operators we emit. A bare value (no prefix) defaults to `>=` — "at least N"
# is the intent behind count search. Mapped through this fixed allowlist so the
# operator is never interpolated from user text into the jsonpath.
_COUNT_COMPARATORS = {
    '>': '>',
    '>=': '>=',
    '<': '<',
    '<=': '<=',
    '=': '==',
}
# Longest-match-first alternation so `>=` wins over `>`. `\s*` tolerates the
# quoted form (`num_subjects:">= 10"`); the bare form never contains spaces.
_COUNT_VALUE_RE = re.compile(r'^(?P<op>>=|<=|>|<|=)?\s*(?P<n>\d+)$')


def _apply_count_filter(
    queryset: QuerySet[Dandiset], jsonpath_path: str, value: str
) -> QuerySet[Dandiset]:
    """Filter dandisets by a numeric count in `Version.metadata` at `jsonpath_path`.

    The value is a non-negative integer, optionally prefixed with a comparator:

    - `num_subjects:10` or `num_subjects:>=10` — at least 10 (bare defaults to `>=`)
    - `num_subjects:>10` / `num_subjects:<10` — strictly above / below
    - `num_subjects:<=10` — at most 10
    - `num_subjects:=10` — exactly 10

    `jsonpath_path` is a trusted constant pointing into `Version.metadata`. The
    comparator is mapped through `_COUNT_COMPARATORS` (never taken verbatim from
    user input) and the integer is bound via `jsonb_path_exists`'s `vars`
    parameter (not inlined into SQL or jsonpath), so the value is injection-safe.

    A dandiset matches if at least one of its versions satisfies the
    predicate. Versions whose metadata lacks the count field don't match —
    the jsonpath `?` filter drops missing/null/non-numeric values naturally.
    """
    match = _COUNT_VALUE_RE.match(value)
    if match is None:
        raise SearchSyntaxError(
            f'Invalid count value {value!r}. Use a non-negative integer, optionally '
            'prefixed with a comparator — e.g. `num_subjects:10`, `num_subjects:>=5`, '
            '`num_subjects:<100`, `num_subjects:=0`.'
        )
    op = _COUNT_COMPARATORS[match.group('op') or '>=']
    n = int(match.group('n'))
    jsonpath = f'{jsonpath_path} ? (@ {op} $val)'
    vars_json = json.dumps({'val': n})
    where = 'jsonb_path_exists(metadata, %s::jsonpath, %s::jsonb)'
    matching_versions = Version.objects.all().extra(  # noqa: S610
        where=[where], params=[jsonpath, vars_json]
    )
    return queryset.filter(id__in=matching_versions.values('dandiset_id'))


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

    # Semantics: every operator describes a property of the dandiset, and
    # multiple operators are AND'd at the dandiset level — NOT at the asset
    # or version level. So `species:mouse species:rat` returns dandisets that
    # have at least one mouse asset AND at least one rat asset (possibly the
    # same asset, possibly different ones). Each asset operator therefore
    # builds an independent AssetSearch subquery and we filter dandisets to
    # those whose IDs appear in EVERY such subquery.
    #
    # Contributor predicates are different: they apply to a single Version's
    # metadata.contributor[] array (since contributors live on the version,
    # not on individual assets), so we accumulate them and AND on the same
    # Version to avoid cross-version weirdness when a draft and a published
    # version have disjoint contributor lists. Within that single version
    # each predicate independently scans `contributor[*]`, so two operators
    # may match different contributor entries.
    annotated: set[str] = set()
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
            asset_match = _apply_asset_filter(AssetSearch.objects.visible_to(user), key, value)
            queryset = queryset.filter(id__in=asset_match.values('dandiset_id'))
        elif key in OWNER_OPS:
            queryset = _apply_owner_filter(queryset, value)
        elif key in CONTRIBUTOR_ROLE_OPS:
            contributor_wheres.append(_contributor_where(value, CONTRIBUTOR_ROLE_OPS[key]))
        elif key in AFFILIATION_OPS:
            contributor_wheres.append(_affiliation_where(value))
        elif key in COUNT_OPS:
            queryset = _apply_count_filter(queryset, COUNT_OPS[key], value)

    if contributor_wheres:
        queryset = _apply_contributor_filters(queryset, contributor_wheres)

    return queryset
