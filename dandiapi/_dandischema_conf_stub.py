from __future__ import annotations

from enum import Enum
import os
from typing import TYPE_CHECKING

from pydantic import AnyHttpUrl, BaseModel

# needs to define at least Config and get_instance_config

if TYPE_CHECKING:
    # This is just a placeholder for static type checking
    class License(Enum): ...  # fmt: skip
else:
    License = Enum(
        'License',
        [('spdx:' + id_,) * 2 for id_ in ['CC0-1.0', 'CC-BY-4.0']],
    )


class Config(BaseModel):
    """Stub Configuration for the DANDI schema."""

    instance_name: str
    """Name of the DANDI instance"""

    instance_identifier: str | None
    """
    ID identifying the DANDI service instance

    Note
    ----
        This field currently only accepts Research Resource Identifiers (RRIDs).
    """

    instance_url: AnyHttpUrl | None
    """
    The URL of the DANDI instance
    """

    doi_prefix: str | None
    """
    The DOI prefix at DataCite
    """

    licenses: set[License] = {License('spdx:CC0-1.0'), License('spdx:CC-BY-4.0')}
    """
    Set of licenses to be supported by the DANDI instance
    """


def get_instance_config() -> Config:
    """Get schema instance config for DANDI Archive."""
    return Config(
        instance_name='DANDI',
        instance_identifier='RRID:SCR_017571',
        instance_url=os.environ.get('DJANGO_DANDI_WEB_APP_URL'),
        doi_prefix=os.environ.get('DJANGO_DANDI_DOI_API_PREFIX'),
    )
