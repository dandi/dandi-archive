from __future__ import annotations

import copy

from dandischema.consts import DANDI_SCHEMA_VERSION

from dandiapi.api.models.version import Version

CONTACT_PERSON_ROLE = 'dcite:ContactPerson'


def _normalize_contributor(version_metadata: dict, name: str, email: str) -> dict:
    """
    Modify `version_metadata` to ensure the contributor field is the correct shape.

    This function ensures that the contributor field is properly formed, and that there is an
    entry in this field with the role of contact person. This field is used in other parts of the
    codebase, so it's important to process this.
    """
    default_contributor = {
        'name': name,
        'email': email,
        'roleName': [CONTACT_PERSON_ROLE],
        'schemaKey': 'Person',
        'affiliation': [],
        'includeInCitation': True,
    }

    # Ensure that the contributor field is of the correct shape
    contributor = version_metadata.get('contributor')
    if not isinstance(contributor, list):
        version_metadata['contributor'] = [default_contributor]
        return version_metadata

    # We know contributor field is a list, but the values could be anything.
    # Filter the value to be only dicts.
    version_metadata['contributor'] = [cont for cont in contributor if isinstance(cont, dict)]

    contributor = version_metadata['contributor']

    # Check if author exists. If not, we will set the default contributor
    author_contributor = next(
        (cont for cont in contributor if cont.get('name') == name and cont.get('email') == email),
        None,
    )
    if not author_contributor:
        contributor.append(default_contributor)
        return version_metadata

    # Ensure the contact person role exists in the author contributor
    roles = author_contributor.get('roleName')
    if not isinstance(roles, list):
        author_contributor['roleName'] = [CONTACT_PERSON_ROLE]
        return version_metadata

    if CONTACT_PERSON_ROLE not in roles:
        roles.append(CONTACT_PERSON_ROLE)

    return version_metadata


def _normalize_version_metadata(raw_version_metadata: dict, name: str, email: str) -> dict:
    """
    Take raw version metadata and convert it into something suitable to be used in a formal Version.

    This could overwrite fields in the raw version metadata.
    """
    # Strip away any computed fields
    version_metadata = copy.deepcopy(Version.strip_metadata(raw_version_metadata))

    version_metadata['schemaKey'] = 'Dandiset'
    version_metadata.setdefault('schemaVersion', DANDI_SCHEMA_VERSION)
    _normalize_contributor(version_metadata, name, email)

    return version_metadata
