from __future__ import annotations

from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime
import heapq
from pathlib import Path
import re
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.files.base import ContentFile

if TYPE_CHECKING:
    from dandiapi.zarr.models import EmbargoedZarrArchive, ZarrArchive

from dandischema.digests.zarr import (
    EMPTY_CHECKSUM,
    ZarrChecksum,
    ZarrChecksumListing,
    ZarrChecksums,
    ZarrJSONChecksumSerializer,
)

ZARR_CHECKSUM_REGEX = r'([0-9a-f]+)-(\d+)--(\d+)'


def parse_zarr_checksum(checksum: str | None) -> dict[str, int]:
    """Return a dict with keys `digest`, `count` and `size`."""
    if checksum is None:
        return parse_zarr_checksum(EMPTY_CHECKSUM)

    match = re.match(ZARR_CHECKSUM_REGEX, checksum)
    if match is None:
        raise Exception('Invalid zarr checksum provided.')

    digest, count, size = match.groups()
    return {
        'digest': digest,
        'count': int(count),
        'size': int(size),
    }


class ZarrChecksumFileUpdater(AbstractContextManager):
    """
    A utility class specifically for updating zarr checksum files.

    When used as a context manager, the checksum file will be loaded and written to automatically.
    """

    _default_serializer = ZarrJSONChecksumSerializer()

    def __init__(
        self,
        zarr_archive: ZarrArchive | EmbargoedZarrArchive,
        zarr_directory_path: str | Path,
        serializer=_default_serializer,
    ):
        self.zarr_archive = zarr_archive
        self.zarr_directory_path = f'{str(zarr_directory_path)}/'
        if self.zarr_directory_path in ['/', './']:
            self.zarr_directory_path = ''
        self._serializer = serializer

        # This is loaded when an instance is used as a context manager,
        # then saved when the context manager exits.
        self._checksums = None

    def __enter__(self):
        existing_zarr_checksum = self.read_checksum_file()
        if existing_zarr_checksum:
            self._checksums = existing_zarr_checksum.checksums
        else:
            self._checksums = ZarrChecksums()
        return self

    def __exit__(self, exc_type, *exc):
        # If there was an exception, do not write anything
        if exc_type:
            return None  # this means throw the exception as normal
        if not self.checksum_listing.checksums.is_empty:
            self.write_checksum_file(self.checksum_listing)
        else:
            # If there are no checksums to write, simply delete the checksum file.
            self.delete_checksum_file()

    @property
    def checksum_file_path(self):
        """Generate the path of the checksum file to update."""
        return f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}{settings.DANDI_ZARR_CHECKSUM_PREFIX_NAME}/{self.zarr_archive.zarr_id}/{self.zarr_directory_path}.checksum'  # noqa: E501

    @property
    def checksum_listing(self) -> ZarrChecksumListing:
        """Get the current state of the updater."""
        if self._checksums is None:
            raise ValueError('This method is only valid when used by a context manager')
        return self._serializer.generate_listing(self._checksums)

    def read_checksum_file(self) -> ZarrChecksumListing | None:
        """Load a checksum listing from the checksum file."""
        storage = self.zarr_archive.storage
        checksum_path = self.checksum_file_path
        if storage.exists(checksum_path):
            with storage.open(checksum_path) as f:
                x = f.read()
                return self._serializer.deserialize(x)
        else:
            return None

    def write_checksum_file(self, zarr_checksum: ZarrChecksumListing):
        """Write a checksum listing to the checksum file."""
        storage = self.zarr_archive.storage
        content_file = ContentFile(self._serializer.serialize(zarr_checksum).encode('utf-8'))
        # save() will never overwrite an existing file, it simply appends some garbage to ensure
        # uniqueness. _save() is an internal storage API that will overwite existing files.
        storage._save(self.checksum_file_path, content_file)

    def delete_checksum_file(self):
        """Delete the checksum file."""
        storage = self.zarr_archive.storage
        storage.delete(self.checksum_file_path)

    def add_file_checksums(self, checksums: list[ZarrChecksum]):
        """Add a list of file checksums to the listing."""
        if self._checksums is None:
            raise ValueError('This method is only valid when used by a context manager')
        self._checksums.add_file_checksums(checksums)

    def add_directory_checksums(self, checksums: list[ZarrChecksum]):
        """Add a list of directory checksums to the listing."""
        if self._checksums is None:
            raise ValueError('This method is only valid when used by a context manager')
        self._checksums.add_directory_checksums(checksums)

    def remove_checksums(self, paths: list[str]):
        """Remove a list of paths from the listing."""
        if self._checksums is None:
            raise ValueError('This method is only valid when used by a context manager')
        self._checksums.remove_checksums([Path(path).name for path in paths])


class SessionZarrChecksumFileUpdater(ZarrChecksumFileUpdater):
    """Override ZarrChecksumFileUpdater to ignore old files."""

    def __init__(self, *args, session_start: datetime, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the start of when new files may have been written
        self._session_start = session_start

    def read_checksum_file(self) -> ZarrChecksumListing | None:
        """Load a checksum listing from the checksum file."""
        storage = self.zarr_archive.storage
        checksum_path = self.checksum_file_path

        # Check if this file was modified during this session
        read_existing = False
        if storage.exists(checksum_path):
            read_existing = storage.modified_time(self.checksum_file_path) >= self._session_start

        # Read existing file if necessary
        if read_existing:
            with storage.open(checksum_path) as f:
                x = f.read()
                return self._serializer.deserialize(x)
        else:
            return None


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


class ZarrChecksumUpdater:
    """A helper for updating batches of checksums in a zarr archive."""

    def __init__(self, zarr_archive: ZarrArchive | EmbargoedZarrArchive) -> None:
        self.zarr_archive = zarr_archive

    def apply_modification(self, modification: ZarrChecksumModification) -> ZarrChecksumFileUpdater:
        with ZarrChecksumFileUpdater(self.zarr_archive, modification.path) as file_updater:
            # Removing a checksum takes precedence over adding/modifying that checksum
            file_updater.add_file_checksums(modification.files_to_update)
            file_updater.add_directory_checksums(modification.directories_to_update)
            file_updater.remove_checksums(modification.paths_to_remove)

        return file_updater

    def modify(self, modifications: ZarrChecksumModificationQueue):
        while not modifications.empty:
            modification = modifications.pop_deepest()
            print(
                f'Applying modifications to {self.zarr_archive.zarr_id}:{modification.path} '
                f'({len(modification.files_to_update)} files, '
                f'{len(modification.directories_to_update)} directories, '
                f'{len(modification.paths_to_remove)} removals)'
            )

            # Apply modification
            file_updater = self.apply_modification(modification)

            # If we have reached the root node, then we obviously do not need to update the parent.
            if modification.path != Path('.') and modification.path != Path('/'):
                if file_updater.checksum_listing.checksums.is_empty:
                    # We have removed all checksums from this checksum file.
                    # ZarrChecksumFileUpdater will have already deleted the checksum file, so all
                    # we need to do is queue this checksum for removal with it's parent.
                    modifications.queue_removal(modification.path.parent, modification.path)
                else:
                    # The parent needs to incorporate the checksum modification we just made.
                    modifications.queue_directory_update(
                        modification.path.parent,
                        ZarrChecksum(
                            name=modification.path.name,
                            digest=file_updater.checksum_listing.digest,
                            size=file_updater.checksum_listing.size,
                        ),
                    )

    def update_file_checksums(self, checksums: Mapping[str, ZarrChecksum]):
        """
        Update the given checksums.

        checksums: a mapping of path to the new checksum for that path.
        """
        modifications = ZarrChecksumModificationQueue()
        for path, checksum in checksums.items():
            modifications.queue_file_update(Path(path).parent, checksum)
        self.modify(modifications)

    def remove_checksums(self, paths: list[str]):
        modifications = ZarrChecksumModificationQueue()
        for path in paths:
            modifications.queue_removal(Path(path).parent, path)
        self.modify(modifications)


class SessionZarrChecksumUpdater(ZarrChecksumUpdater):
    """ZarrChecksumUpdater to distinguish existing and new checksum files."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Set microseconds to zero, since the timestamp from S3/Minio won't include them
        # Failure to set this to zero will result in false negatives
        self._session_start = datetime.now().replace(tzinfo=None, microsecond=0)

    def apply_modification(
        self, modification: ZarrChecksumModification
    ) -> SessionZarrChecksumFileUpdater:
        with SessionZarrChecksumFileUpdater(
            zarr_archive=self.zarr_archive,
            zarr_directory_path=modification.path,
            session_start=self._session_start,
        ) as file_updater:
            file_updater.add_file_checksums(modification.files_to_update)
            file_updater.add_directory_checksums(modification.directories_to_update)
            file_updater.remove_checksums(modification.paths_to_remove)

        return file_updater
