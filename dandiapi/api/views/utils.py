from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DandisetSerializerContext:
    star_count: int
    starred_by_current_user: bool
