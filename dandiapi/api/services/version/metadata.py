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
        'contributor': [],
        **version_metadata,
    }
    # if function did not receive already a record for that name
    # we create one:
    if not any(r.get('name') == name for r in version_metadata['contributor']):
        version_metadata['contributor'].insert(
            0,
            {
                'name': name,
                'email': email,
                'roleName': ['dcite:ContactPerson'],
                'schemaKey': 'Person',
                'affiliation': [],
                'includeInCitation': True,
            },
        )
    # Run the version_metadata through the pydantic model to automatically include any boilerplate
    # like the access or repository fields
    return PydanticDandiset.model_construct(**version_metadata).model_dump(
        mode='json', exclude_none=True
    )
