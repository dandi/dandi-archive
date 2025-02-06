from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dandiapi.api.models.version import Version


@dataclass
class DandisetSerializerContext:
    star_count: int
    starred_by_current_user: bool
    latest_version: Version
