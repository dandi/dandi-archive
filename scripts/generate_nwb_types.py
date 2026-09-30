"""Regenerate `dandiapi/api/services/search/nwb_types.json`.

The `variable:` and `technique:` search operators expand a value to the NWB
neurodata types that extend it. The archive doesn't depend on pynwb or dandi-cli
at runtime, so this snapshots the type hierarchy from pynwb's namespace catalog
and the type -> measurement technique map from dandi-cli. Re-run it after bumping
either package:

    uv run --no-project --with pynwb --with dandi scripts/generate_nwb_types.py
"""

from __future__ import annotations

import json
from pathlib import Path

import dandi
from dandi.metadata.util import neurodata_typemap
import pynwb

OUTPUT = Path(__file__).parents[1] / 'dandiapi' / 'api' / 'services' / 'search' / 'nwb_types.json'


def main():
    catalog = pynwb.get_type_map().namespace_catalog
    parents = {}
    for namespace in catalog.namespaces:
        for type_name in catalog.get_namespace(namespace).get_registered_types():
            parents[type_name] = catalog.get_spec(namespace, type_name).data_type_inc

    techniques = {
        type_name: entry['technique']
        for type_name, entry in neurodata_typemap.items()
        if entry['technique']
    }

    data = {
        'generated_by': 'scripts/generate_nwb_types.py',
        'pynwb_version': pynwb.__version__,
        'dandi_version': dandi.__version__,
        'parents': dict(sorted(parents.items())),
        'techniques': dict(sorted(techniques.items())),
    }
    OUTPUT.write_text(json.dumps(data, indent=2) + '\n')


if __name__ == '__main__':
    main()
