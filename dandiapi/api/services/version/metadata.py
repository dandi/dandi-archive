from __future__ import annotations

from typing import Any

from dandischema.consts import DANDI_SCHEMA_VERSION

from dandiapi.api.models.version import Version


def _is_empty_record(data: Any) -> bool:
    return isinstance(data, dict) and data.keys() == {'schemaKey'}


def strip_empty_records(data: Any) -> Any:
    """
    Return a copy of ``data`` without records holding only a ``schemaKey``.

    See https://github.com/dandi/dandi-archive/issues/2944
    """
    if isinstance(data, list):
        items = (strip_empty_records(item) for item in data)
        return [item for item in items if not _is_empty_record(item)]
    if isinstance(data, dict):
        pairs = ((key, strip_empty_records(value)) for key, value in data.items())
        return {key: value for key, value in pairs if not _is_empty_record(value)}
    return data


def _normalize_version_metadata(raw_version_metadata: dict, name: str, email: str) -> dict:
    """
    Take raw version metadata and convert it into something suitable to be used in a formal Version.

    This could overwrite fields in the raw version metadata.
    """
    # Strip away any computed fields and empty records
    version_metadata = strip_empty_records(Version.strip_metadata(raw_version_metadata))

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
