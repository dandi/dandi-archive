"""NWB neurodata type hierarchy, used to expand `variable:` and `technique:` search values.

`assetsSummary.variableMeasured` records only the neurodata types actually present
in a dandiset's files, never their ancestors, and `measurementTechnique` is derived
from those same types. So a search for a parent type (e.g. `PatchClampSeries`) or
its technique (`patch clamp`) would miss dandisets that only contain subtypes
(`CurrentClampSeries`, `VoltageClampSeries`, ...). These helpers expand a query
value to the names of every matching subtype so the filter can match them too.

The archive doesn't depend on pynwb or dandi-cli at runtime, so the hierarchy and
dandi-cli's type -> technique map are snapshotted in `nwb_types.json`. Regenerate
it with `scripts/generate_nwb_types.py`.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

_DATA = json.loads(Path(__file__).with_name('nwb_types.json').read_text())

# Neurodata type -> the type it extends. Types without a parent aren't listed.
_PARENTS: dict[str, str] = _DATA['parents']
# Neurodata type -> the measurement technique dandi-cli assigns to it.
_TECHNIQUES: dict[str, str] = _DATA['techniques']

_CHILDREN: dict[str, list[str]] = defaultdict(list)
for _type_name, _parent in _PARENTS.items():
    _CHILDREN[_parent].append(_type_name)

_TYPES_BY_LOWER_NAME = {
    type_name.lower(): type_name for type_name in (*_PARENTS, *_PARENTS.values())
}


def _with_descendants(type_name: str) -> set[str]:
    found = {type_name}
    stack = [type_name]
    while stack:
        for child in _CHILDREN[stack.pop()]:
            if child not in found:
                found.add(child)
                stack.append(child)
    return found


def expand_variable(value: str) -> set[str]:
    """Return the neurodata types a `variable:` value should also match exactly.

    If `value` names a known NWB type (case-insensitively), that's the type and
    all of its subtypes; otherwise nothing. Generic base types such as
    `NWBDataInterface` are left out of the snapshot, so they never expand.
    """
    type_name = _TYPES_BY_LOWER_NAME.get(value.lower())
    if type_name is None:
        return set()
    return _with_descendants(type_name)


def expand_technique(value: str) -> set[str]:
    """Return the technique names a `technique:` value should also match exactly.

    Finds every type whose technique contains `value` (case-insensitively), and
    returns the techniques of those types and all of their subtypes.
    """
    needle = value.lower()
    related_types: set[str] = set()
    for type_name, technique in _TECHNIQUES.items():
        if needle in technique.lower():
            related_types |= _with_descendants(type_name)
    return {_TECHNIQUES[t] for t in related_types if t in _TECHNIQUES}
