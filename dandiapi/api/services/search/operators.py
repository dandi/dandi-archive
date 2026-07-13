"""Operator vocabulary and dispatch tables for the advanced-search syntax.

Pure-Python module so :mod:`parser` (which knows nothing about Django) can
import the operator allowlist alongside the filter dispatch tables. Adding
a new operator is one entry in the relevant table here; the parser picks
it up automatically via :data:`OPERATOR_KEYS`.
"""

from __future__ import annotations

# File-type operator: short name → MIME prefix matched with istartswith.
# Keep in sync with DandisetSearchQueryParameterSerializer.
FILE_TYPE_ALIASES = {
    'nwb': 'application/x-nwb',
    'image': 'image/',
    'text': 'text/',
    'video': 'video/',
}

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

ASSET_OPS = frozenset({'species', 'approach', 'technique', 'file_type'})

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

# Numeric count operators: short name → jsonpath into `Version.metadata`.
# Value is a non-negative integer, optionally prefixed with a comparator
# (`>`, `>=`, `<`, `<=`, `=`); a bare value means `>=`. So `num_subjects:10`
# and `num_subjects:>=10` both match dandisets whose
# `assetsSummary.numberOfSubjects` is at least 10, while `num_subjects:<5` and
# `num_subjects:=0` match below / exact. The bare-defaults-to-"at least"
# behavior reflects the intent behind count search ("studies with at least N
# <thing>"). Comparator parsing lives in `filters._apply_count_filter`.
#
# Only `num_subjects` is exposed for now. The `assetsSummary` schema also
# carries `numberOfFiles`, `numberOfBytes`, `numberOfSamples`, and
# `numberOfCells` — each would be a one-line entry here.
#
# `num_sessions` is intentionally absent: dandischema's `AssetsSummary` does
# not aggregate sessions, and there is no per-asset `sessionId` field from
# which to derive a count. Adding a `num_sessions:` operator would require
# upstream schema work.
COUNT_OPS: dict[str, str] = {
    'num_subjects': '$.assetsSummary.numberOfSubjects',
}

# Asset-name jsonpaths: each operator selects a different array path on
# `asset_metadata` whose elements have a `.name` we substring-match against.
# Paths MUST be trusted constants (interpolated into the SQL).
ASSET_NAME_PATH_OPS = {
    'species': '$.wasAttributedTo[*].species.name',
    'approach': '$.approach[*].name',
    'technique': '$.measurementTechnique[*].name',
}

# Union of every operator key. The parser uses this for its allowlist;
# adding a new operator anywhere above is automatically known to the parser.
OPERATOR_KEYS: frozenset[str] = (
    DATE_OPS
    | ASSET_OPS
    | OWNER_OPS
    | AFFILIATION_OPS
    | frozenset(CONTRIBUTOR_ROLE_OPS)
    | frozenset(COUNT_OPS)
)
