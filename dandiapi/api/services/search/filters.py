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
    'affiliation': 'Affiliation',
    'ethics_approval': 'EthicsApproval',
    'other': 'Other',
}


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


def _contributor_jsonpath(value: str, role: str | None) -> tuple[str, list[str]]:
    """Build a (where_clause, params) for a single contributor element predicate.

    Matches a `contributor[]` element whose `name`, `email`, OR `identifier`
    contains `value` (case-insensitive). The identifier covers ORCIDs for
    Person contributors (e.g. `0000-0002-2990-9889`) and ROR URLs for
    Organization contributors (e.g. `https://ror.org/01cwqze88`); the
    substring match means bare-ID forms like `01cwqze88` work too.

    If `role` is given, additionally requires that element's `roleName` array
    to contain a string matching `role` (also case-insensitive substring).

    Uses the third argument of `jsonb_path_exists` to bind named variables
    (`$val`, `$role`) so the user values are properly quoted by Postgres
    rather than concatenated into the path string.
    """
    name_or_email_or_id = (
        '@.name like_regex $val flag "i" '
        ' || @.email like_regex $val flag "i" '
        ' || @.identifier like_regex $val flag "i"'
    )
    if role is None:
        jsonpath = f'$.contributor[*] ? ({name_or_email_or_id})'
        vars_obj = {'val': re.escape(value)}
    else:
        jsonpath = (
            '$.contributor[*] ? '
            f'(({name_or_email_or_id}) '
            '  && exists(@.roleName[*] ? (@ like_regex $role flag "i")))'
        )
        vars_obj = {'val': re.escape(value), 'role': re.escape(role)}
    where = f"jsonb_path_exists(metadata, '{jsonpath}'::jsonpath, %s::jsonb)"
    return where, [json.dumps(vars_obj)]


def _apply_contributor_filters(
    queryset: QuerySet[Dandiset], specs: list[tuple[str, str | None]]
) -> QuerySet[Dandiset]:
    """Filter dandisets by contributor / per-role operators.

    `specs` is a list of `(value, role_or_None)` pairs. The returned queryset
    is restricted to dandisets that have at least ONE Version whose
    `metadata.contributor[]` satisfies ALL the predicates simultaneously.
    Multiple operators thus AND on the same Version (so a draft and a
    published version with disjoint contributor lists never combine into a
    spurious match).

    Each operator is independent: `author:Baker funder:NIH` matches if SOME
    contributor element has Baker as Author AND SOME contributor element (the
    same OR a different one) has NIH as Funder.
    """
    matching_versions = Version.objects.all()
    for value, role in specs:
        where, params = _contributor_jsonpath(value, role)
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
    # Contributor specs collected here, then applied in a single batch so all
    # operators AND on the same Version (avoids cross-version weirdness when
    # a dandiset has both a draft and a published version with disjoint
    # contributor lists).
    contributor_specs: list[tuple[str, str | None]] = []

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
        elif key in _CONTRIBUTOR_ROLE_OPS:
            contributor_specs.append((value, _CONTRIBUTOR_ROLE_OPS[key]))

    if contributor_specs:
        queryset = _apply_contributor_filters(queryset, contributor_specs)

    if summary_clauses:
        queryset = _apply_summary_filters(queryset, summary_clauses)

    return queryset
