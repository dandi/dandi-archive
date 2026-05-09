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

# Contributor / per-role operators. The catch-all `contributor:` matches any
# role; each named operator additionally requires the matched contributor's
# `roleName` array to contain the corresponding `dcite:Role` value. Keys MUST
# be in OPERATOR_KEYS (parser allowlist) — keep the two in sync.
#
# Independent-operator semantics: each operator constrains a single
# `contributor[]` element, but two operators (e.g. `author:Baker funder:NIH`)
# are AND'd against the same Version's metadata — they may match the same OR
# different contributor elements. Same composability as the asset operators.
_CONTRIBUTOR_ROLE_OPS: dict[str, str | None] = {
    'contributor': None,  # catch-all, no role constraint
    'author': 'Author',
    'conceptualization': 'Conceptualization',
    'contact_person': 'ContactPerson',
    'data_collector': 'DataCollector',
    'data_curator': 'DataCurator',
    'data_manager': 'DataManager',
    'formal_analysis': 'FormalAnalysis',
    'funding_acquisition': 'FundingAcquisition',
    'investigation': 'Investigation',
    'maintainer': 'Maintainer',
    'methodology': 'Methodology',
    'producer': 'Producer',
    'project_leader': 'ProjectLeader',
    'project_manager': 'ProjectManager',
    'project_member': 'ProjectMember',
    'project_administration': 'ProjectAdministration',
    'researcher': 'Researcher',
    'resources': 'Resources',
    'software': 'Software',
    'supervision': 'Supervision',
    'validation': 'Validation',
    'visualization': 'Visualization',
    'funder': 'Funder',
    'sponsor': 'Sponsor',
    'study_participant': 'StudyParticipant',
    # Note: `affiliation` is intentionally NOT here. Despite `dcite:Affiliation`
    # existing as a RoleType, in real DANDI data affiliations live in a
    # separate nested field — `Person.affiliation[]` — not as a contributor's
    # role. The `affiliation:` operator queries that nested path; see
    # `_AFFILIATION_JSONPATH` below.
}

# Affiliation has its own jsonpath because it lives at
# `contributor[].affiliation[]`, not `contributor[].roleName[]`.
_AFFILIATION_JSONPATH = (
    '$.contributor[*].affiliation[*] ? '
    '(@.name like_regex $val flag "i" '
    ' || @.identifier like_regex $val flag "i")'
)


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


def _apply_owner_filter(queryset: QuerySet[Dandiset], value: str) -> QuerySet[Dandiset]:
    """Filter dandisets to those owned by the given user identifier.

    `value` is matched case-insensitively against `User.username`, `User.email`,
    `User.first_name`, `User.last_name`, or `"first_name last_name"` (so the
    display name shown in the UI works). Multiple users may match; we union
    dandisets owned by any of them. Unknown user → empty result.
    """
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
    """Jsonpath + vars for a contributor[] element predicate.

    Matches a `contributor[]` element whose `name`, `email`, OR `identifier`
    contains `value` (case-insensitive). The identifier covers ORCIDs for
    Person contributors (e.g. `0000-0002-2990-9889`) and ROR URLs for
    Organization contributors (e.g. `https://ror.org/01cwqze88`); the
    substring match means bare-ID forms like `01cwqze88` work too.

    If `role` is given, additionally requires that element's `roleName` array
    to contain a string matching `role` (also case-insensitive substring).
    """
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
    """Wrap a jsonpath + vars into a `jsonb_path_exists(metadata, ...)` predicate.

    Uses the third argument of `jsonb_path_exists` to bind named variables
    so user values are properly quoted by Postgres rather than concatenated
    into the path string.
    """
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
            queryset = _apply_owner_filter(queryset, value)
        elif key in _CONTRIBUTOR_ROLE_OPS:
            jsonpath, vars_obj = _contributor_role_jsonpath(value, _CONTRIBUTOR_ROLE_OPS[key])
            contributor_wheres.append(_build_jsonpath_where(jsonpath, vars_obj))
        elif key == 'affiliation':
            contributor_wheres.append(
                _build_jsonpath_where(_AFFILIATION_JSONPATH, {'val': re.escape(value)})
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
