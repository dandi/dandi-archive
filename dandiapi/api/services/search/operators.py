"""Operator vocabulary and dispatch tables for the advanced-search syntax.

Pure-Python module so :mod:`parser` (which knows nothing about Django) can
import the operator allowlist alongside the filter dispatch tables. Adding
a new operator is one entry in the relevant table here; the parser picks
it up automatically via :data:`OPERATOR_KEYS`.
"""

from __future__ import annotations

DATE_OPS = frozenset(
    {
        'created_before',
        'created_after',
        'modified_before',
        'modified_after',
        'published_before',
        'published_after',
    }
)

# Maps each operator to a Postgres jsonpath into the version-level
# `assetsSummary` aggregation. Paths MUST be trusted constants: they're
# interpolated into the SQL. `variableMeasured` holds bare strings rather
# than objects with a `name`, so its path selects the elements themselves.
SUMMARY_PATH_OPS = {
    'species': '$.assetsSummary.species[*].name',
    'approach': '$.assetsSummary.approach[*].name',
    'technique': '$.assetsSummary.measurementTechnique[*].name',
    'standard': '$.assetsSummary.dataStandard[*].name',
    'variable': '$.assetsSummary.variableMeasured[*]',
}

OWNER_OPS = frozenset({'owner'})

# Per-role contributor operators: snake_case operator → PascalCase
# `dandischema.RoleType.name`. The catch-all `contributor:` matches any
# role; each named operator additionally requires the matched contributor's
# `roleName` array to contain `dcite:<RoleName>`.
#
# Kept as an explicit allowlist (rather than auto-derived from RoleType) so
# schema-level renames or additions can't silently change the public search
# syntax. A unit test validates each value against `RoleType.name`.
CONTRIBUTOR_ROLE_OPS: dict[str, str | None] = {
    'contributor': None,  # catch-all
    'author': 'Author',
    'contact_person': 'ContactPerson',
    'data_collector': 'DataCollector',
    'data_curator': 'DataCurator',
    'data_manager': 'DataManager',
    'maintainer': 'Maintainer',
    'project_leader': 'ProjectLeader',
    'funder': 'Funder',
    'sponsor': 'Sponsor',
    # The other RoleType values exist on `dandischema` but aren't exposed as
    # search operators — see PR discussion. The catch-all `contributor:` still
    # finds anyone in any role; only the role-restricting shortcuts are pruned.
}

AFFILIATION_OPS = frozenset({'affiliation'})

# Numeric count operators: short name -> jsonpath into `Version.metadata`.
# The value is a non-negative integer, optionally prefixed with a comparator
# (`>`, `>=`, `<`, `<=`, `=`). A bare value is an exact match, as in GitHub's
# `comments:10`, so `num_subjects:10` and `num_subjects:=10` mean the same
# thing and `num_subjects:>=10` is the query for "at least 10". Comparator
# parsing lives in `filters._count_where`.
#
# Only `num_subjects` is exposed for now. The `assetsSummary` schema also
# carries `numberOfFiles`, `numberOfBytes`, `numberOfSamples`, and
# `numberOfCells`; each would be a one-line entry here.
#
# `num_sessions` is absent because dandischema's `AssetsSummary` does not
# aggregate sessions and assets have no `sessionId` field to count.
COUNT_OPS: dict[str, str] = {
    'num_subjects': '$.assetsSummary.numberOfSubjects',
}

# Union of every operator key. The parser uses this for its allowlist;
# adding a new operator anywhere above is automatically known to the parser.
OPERATOR_KEYS: frozenset[str] = (
    DATE_OPS
    | frozenset(SUMMARY_PATH_OPS)
    | OWNER_OPS
    | AFFILIATION_OPS
    | frozenset(CONTRIBUTOR_ROLE_OPS)
    | frozenset(COUNT_OPS)
)
