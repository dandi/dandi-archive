from __future__ import annotations

from dandischema.models import Dandiset as PydanticDandiset
from django.conf import settings

from dandiapi.api.models.version import Version


def _normalize_version_metadata(
    raw_version_metadata: dict, name: str, email: str, *, embargo: bool
) -> dict:
    """
    Take raw version metadata and convert it into something suitable to be used in a formal Version.

    This could overwrite fields in the raw version metadata.
    """
    # Strip away any computed fields
    version_metadata = Version.strip_metadata(raw_version_metadata)

    # Only inject a schemaVersion and default contributor field if they are
    # not specified in the version_metadata
    version_metadata = {
        'schemaKey': 'Dandiset',
        'schemaVersion': settings.DANDI_SCHEMA_VERSION,
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
        # TODO: move this into dandischema
        'access': [
            {
                'schemaKey': 'AccessRequirements',
                'status': 'dandi:EmbargoedAccess' if embargo else 'dandi:OpenAccess',
            }
        ],
        **version_metadata,
    }
    # Run the version_metadata through the pydantic model to automatically include any boilerplate
    # like the access or repository fields
    return PydanticDandiset.unvalidated(**version_metadata).json_dict()
