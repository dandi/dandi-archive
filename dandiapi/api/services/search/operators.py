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

ASSET_OPS = frozenset({'species', 'approach', 'technique', 'standard', 'file_type'})

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
    # Operator name intentionally shorter than the schema name (`ProjectLeader`).
    'project_lead': 'ProjectLeader',
    'funder': 'Funder',
    'sponsor': 'Sponsor',
    # The other RoleType values exist on `dandischema` but aren't exposed as
    # search operators — see PR discussion. The catch-all `contributor:` still
    # finds anyone in any role; only the role-restricting shortcuts are pruned.
}

AFFILIATION_OPS = frozenset({'affiliation'})

# Asset-name jsonpaths: each operator selects a different array path on
# `asset_metadata` whose elements have a `.name` we substring-match against.
# Paths MUST be trusted constants (interpolated into the SQL).
ASSET_NAME_PATH_OPS = {
    'species': '$.wasAttributedTo[*].species.name',
    'approach': '$.approach[*].name',
    'technique': '$.measurementTechnique[*].name',
    'standard': '$.dataStandard[*].name',
}

# Affiliation jsonpath: nested under each contributor[].affiliation[],
# matched on the affiliation's own `name` or `identifier` (ROR URL).
AFFILIATION_JSONPATH = (
    '$.contributor[*].affiliation[*] ? '
    '(@.name like_regex $val flag "i" '
    ' || @.identifier like_regex $val flag "i")'
)

# Union of every operator key. The parser uses this for its allowlist;
# adding a new operator anywhere above is automatically known to the parser.
OPERATOR_KEYS: frozenset[str] = (
    DATE_OPS | ASSET_OPS | OWNER_OPS | AFFILIATION_OPS | frozenset(CONTRIBUTOR_ROLE_OPS)
)
