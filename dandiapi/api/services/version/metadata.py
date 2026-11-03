from __future__ import annotations

from typing import Any

from dandischema.consts import DANDI_SCHEMA_VERSION

from dandiapi.api.models.version import Version


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str | list | dict) and not value)


def _strip_empty_records(data: Any) -> Any:
    """Return a copy of ``data`` with the empty records within it removed."""
    if isinstance(data, list):
        items = [_strip_empty_records(item) for item in data]
        return [item for item in items if not is_empty_record(item)]
    if isinstance(data, dict):
        stripped = {}
        for key, value in data.items():
            new_value = _strip_empty_records(value)
            if not is_empty_record(new_value):
                stripped[key] = new_value
        return stripped
    return data


def is_empty_record(data: Any) -> bool:
    """
    Whether ``data`` is a metadata record which carries no information.

    A record is a JSON object with a ``schemaKey``. It is empty if every other
    field is ``null``, an empty string, an empty list or an empty object,
    e.g. ``{"schemaKey": "ContactPoint"}``.
    """
    return (
        isinstance(data, dict)
        and 'schemaKey' in data
        and all(_is_blank(value) for key, value in data.items() if key != 'schemaKey')
    )


def strip_empty_records(metadata: dict) -> dict:
    """
    Return a copy of ``metadata`` without the empty records nested within it.

    Empty records (see `is_empty_record`) are dropped from lists, and removed
    together with their key from objects. Records are cleaned bottom-up, so a
    record which only contained empty records becomes empty itself and is
    removed as well. Lists which end up empty are kept, as ``[]``.

    The web metadata editor (Meditor) produces such records whenever it renders
    the form of an optional nested object, e.g. the ``contactPoint`` of an
    ``EthicsApproval``, as it fills in the constant ``schemaKey`` even if the
    user enters nothing. They carry no information, so we remove them from all
    the metadata submitted to the API, whichever client sent it. See
    https://github.com/dandi/dandi-archive/issues/2944
    """
    return _strip_empty_records(metadata)


def _normalize_version_metadata(raw_version_metadata: dict, name: str, email: str) -> dict:
    """
    Take raw version metadata and convert it into something suitable to be used in a formal Version.

    This could overwrite fields in the raw version metadata.
    """
    # Strip away any computed fields, and records which carry no information
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
