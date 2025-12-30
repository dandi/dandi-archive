from __future__ import annotations

import copy

from dandischema.consts import DANDI_SCHEMA_VERSION

from dandiapi.api.models.version import Version


def _normalize_version_metadata(raw_version_metadata: dict, name: str, email: str) -> dict:
    """
    Take raw version metadata and convert it into something suitable to be used in a formal Version.

    This could overwrite fields in the raw version metadata.
    """
    # Strip away any computed fields
    version_metadata = copy.deepcopy(Version.strip_metadata(raw_version_metadata))

    # Only inject a schemaVersion and default contributor field if they are
    # not specified in the version_metadata
    return {
        'schemaKey': 'Dandiset',
        'schemaVersion': DANDI_SCHEMA_VERSION,
        'contributor': [
            {
                'name': name,
                'email': email,
                'roleName': ['dcite:ContactPerson'],
                'schemaKey': 'Person',
                'affiliation': [],
                'includeInCitation': True,
            },
        ],
        **version_metadata,
    }
