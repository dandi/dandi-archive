from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import heapq
from pathlib import Path
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dandiapi.zarr.models import EmbargoedZarrArchive, ZarrArchive

from dandischema.digests.zarr import ZarrChecksum, ZarrJSONChecksumSerializer

ZARR_CHECKSUM_REGEX = r'[0-9a-f]+-(\d+)--(\d+)'


def parse_checksum_string(checksum: str) -> tuple[int, int]:
    """Return a tuple of (file count, total size)."""
    match = re.match(ZARR_CHECKSUM_REGEX, checksum)
    if match is None:
        raise Exception('Invalid zarr checksum provided.')

    count, size = match.groups()
    return (int(count), int(size))


@dataclass
class ZarrChecksumModification:
    """
    A set of changes to apply to a ZarrChecksumListing.

    Additions or modifications are stored in files_to_update and directories_to_update.
    Removals are stored in paths_to_remove.
    """

    path: Path
    files_to_update: list[ZarrChecksum] = field(default_factory=list)
    directories_to_update: list[ZarrChecksum] = field(default_factory=list)
    paths_to_remove: list[str] = field(default_factory=list)

    def __lt__(self, other):
        return str(self.path) < str(other.path)


class ZarrChecksumModificationQueue:
    """
    A queue of modifications to be applied to a zarr archive.

    It is important to apply modifications starting as deep as possible, because every modification
    changes the checksum of its parent, which bubbles all the way up to the top of the tree hash.
    This class makes managing that queue of modifications much easier.
    """

    def __init__(self) -> None:
        self._heap: list[tuple[int, ZarrChecksumModification]] = []
        self._path_map: dict[Path, ZarrChecksumModification] = {}

    def _add_path(self, key: Path):
        modification = ZarrChecksumModification(path=key)

        # Add link to modification
        self._path_map[key] = modification

        # Add modification to heap with length (negated to representa max heap)
        length = len(key.parents)
        heapq.heappush(self._heap, (-1 * length, modification))

    def _get_path(self, key: Path):
        if key not in self._path_map:
            self._add_path(key)

        return self._path_map[key]

    def queue_file_update(self, key: Path, checksum: ZarrChecksum):
        self._get_path(key).files_to_update.append(checksum)

    def queue_directory_update(self, key: Path, checksum: ZarrChecksum):
        self._get_path(key).directories_to_update.append(checksum)

    def queue_removal(self, key: Path, path: Path | str):
        self._get_path(key).paths_to_remove.append(str(path))

    def pop_deepest(self) -> ZarrChecksumModification:
        """Find the deepest path in the queue, and return it and its children to be updated."""
        _, modification = heapq.heappop(self._heap)
        del self._path_map[modification.path]

        return modification

    @property
    def empty(self):
        return len(self._heap) == 0

    def process(self) -> str:
        pass


class ZarrChecksumUpdater:
    """A helper for updating batches of checksums in a zarr archive."""

    def __init__(self, zarr_archive: ZarrArchive | EmbargoedZarrArchive) -> None:
        self.zarr_archive = zarr_archive

    def modify(self, modifications: ZarrChecksumModificationQueue):
        latest_checksum = None
        while not modifications.empty:
            # Pop the deepest directory available
            modification = modifications.pop_deepest()
            print(
                f'Applying modifications to {self.zarr_archive.zarr_id}:{modification.path} '
                f'({len(modification.files_to_update)} files, '
                f'{len(modification.directories_to_update)} directories, '
                f'{len(modification.paths_to_remove)} removals)'
            )

            # Generates a sorted checksum listing for the current path
            checksum_listing = ZarrJSONChecksumSerializer().generate_listing(
                files=modification.files_to_update, directories=modification.directories_to_update
            )
            latest_checksum = checksum_listing

            # If we have reached the root node, then we're done.
            if modification.path == Path('.') or modification.path == Path('/'):
                break

            # The parent needs to incorporate the checksum modification we just made.
            modifications.queue_directory_update(
                modification.path.parent,
                ZarrChecksum(
                    name=modification.path.name,
                    digest=checksum_listing.digest,
                    size=checksum_listing.size,
                ),
            )

        return latest_checksum and latest_checksum.digest
