from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from django.conf import settings
from django.core.files.base import ContentFile

if TYPE_CHECKING:
    from dandiapi.api.models import ZarrArchive


@dataclass(order=True, eq=True, frozen=True)
class ZarrChecksum:
    """
    A checksum for a single file/directory in a zarr file.

    Every file and directory in a zarr archive has a path and a MD5 hash.
    """

    path: str
    # We ignore the checksum for equality purposes to make it easier to apply modifications to a
    # list of ZarrChecksums.
    md5: str = field(compare=False)


@dataclass
class ZarrChecksumListing:
    """
    A listing of checksums for all sub-files/directories in a zarr directory.

    This is the data serialized in the checksum file.
    """

    checksums: List[ZarrChecksum]
    md5: str


class ZarrJSONChecksumSerializer:
    def aggregate_checksum(self, checksums: List[ZarrChecksum]) -> str:
        """Generate an aggregated checksum for a list of ZarrChecksums."""
        # Use the most compact separators possible
        content = json.dumps(
            [asdict(zarr_md5) for zarr_md5 in sorted(checksums)], separators=(',', ':')
        )
        h = hashlib.md5()
        h.update(content.encode('utf-8'))
        return h.hexdigest()

    def serialize(self, zarr_checksum_listing: ZarrChecksumListing) -> str:
        """Serialize a ZarrChecksumListing into a string."""
        return json.dumps(asdict(zarr_checksum_listing))

    def deserialize(self, json_str: str) -> ZarrChecksumListing:
        """Deserialize a string into a ZarrChecksumListing."""
        listing = ZarrChecksumListing(**json.loads(json_str))
        listing.checksums = [ZarrChecksum(**checksum) for checksum in listing.checksums]
        return listing

    def generate_listing(self, checksums: List[ZarrChecksum]) -> ZarrChecksumListing:
        """
        Generate a new ZarrChecksumListing from the given list of checksums.

        This method wraps aggregate_checksum and should not be overriden.
        """
        checksums = sorted(checksums)
        return ZarrChecksumListing(
            checksums=checksums,
            md5=self.aggregate_checksum(checksums),
        )


class ZarrChecksumFileUpdater(AbstractContextManager):
    """
    A utility class specifically for updating zarr checksum files.

    When used as a context manager, the checksum file will be loaded and written to automatically.
    """

    _default_serializer = ZarrJSONChecksumSerializer()

    def __init__(
        self,
        zarr_archive: ZarrArchive,
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
            self._checksums = []
        return self

    def __exit__(self, exc_type, *exc):
        # If there was an exception, do not write anything
        if exc_type:
            return None  # this means throw the exception as normal
        if len(self.checksum_listing.checksums) > 0:
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

    def read_checksum_file(self) -> Optional[ZarrChecksumListing]:
        """Load a checksum listing from the checksum file."""
        from dandiapi.api.models import ZarrUploadFile

        storage = ZarrUploadFile.blob.field.storage
        checksum_path = self.checksum_file_path
        if storage.exists(checksum_path):
            with storage.open(checksum_path) as f:
                x = f.read()
                return self._serializer.deserialize(x)
        else:
            return None

    def write_checksum_file(self, zarr_checksum: ZarrChecksumListing):
        """Write a checksum listing to the checksum file."""
        from dandiapi.api.models import ZarrUploadFile

        storage = ZarrUploadFile.blob.field.storage
        content_file = ContentFile(self._serializer.serialize(zarr_checksum).encode('utf-8'))
        # save() will never overwrite an existing file, it simply appends some garbage to ensure
        # uniqueness. _save() is an internal storage API that will overwite existing files.
        storage._save(self.checksum_file_path, content_file)

    def delete_checksum_file(self):
        """Delete the checksum file."""
        from dandiapi.api.models import ZarrUploadFile

        storage = ZarrUploadFile.blob.field.storage
        storage.delete(self.checksum_file_path)

    def add_checksums(self, checksums: List[ZarrChecksum]):
        """Add a list of checksums to the listing."""
        if self._checksums is None:
            raise ValueError('This method is only valid when used by a context manager')
        for new_checksum in checksums:
            try:
                # O(n) performance, consider an ordered dict for optimization
                self._checksums[self._checksums.index(new_checksum)] = new_checksum
            except ValueError:
                self._checksums.append(new_checksum)
        self._checksums = sorted(self._checksums)

    def remove_checksums(self, paths: List[str]):
        """Remove a list of paths from the listing."""
        if self._checksums is None:
            raise ValueError('This method is only valid when used by a context manager')
        self._checksums = sorted(
            filter(lambda checksum: checksum.path not in paths, self._checksums)
        )


@dataclass
class ZarrChecksumModification:
    """
    A set of changes to apply to a ZarrChecksumListing.

    Additions or modifications are stored in checksums_to_update.
    Removals are stored in paths_to_remove.
    """

    path: Path
    checksums_to_update: list[ZarrChecksum] = field(default_factory=list)
    paths_to_remove: list[str] = field(default_factory=list)


class ZarrChecksumModificationQueue:
    """
    A queue of modifications to be applied to a zarr archive.

    It is important to apply modifications starting as deep as possible, because every modification
    changes the checksum of its parent, which bubbles all the way up to the top of the tree hash.
    This class makes managing that queue of modifications much easier.
    """

    def __init__(self) -> None:
        self._queue: dict[Path, ZarrChecksumModification] = {}

    def queue_update(self, key: Path, checksum: ZarrChecksum):
        if key not in self._queue:
            self._queue[key] = ZarrChecksumModification(key)
        self._queue[key].checksums_to_update.append(checksum)

    def queue_removal(self, key: Path, path: Path | str):
        if key not in self._queue:
            self._queue[key] = ZarrChecksumModification(key)
        self._queue[key].paths_to_remove.append(str(path))

    def pop_deepest(self):
        """Find the deepest path in the queue, and return it and its children to be updated."""
        longest_path = list(self._queue.keys())[0]
        longest_path_length = str(longest_path).split('/')
        # O(n) performance, consider a priority queue for optimization
        for path in self._queue.keys():
            path_length = str(path).split('/')
            if path_length > longest_path_length:
                longest_path = path
                longest_path_length = path_length
        return self._queue.pop(longest_path)

    @property
    def empty(self):
        return len(self._queue) == 0


class ZarrChecksumUpdater:
    """A helper for updating batches of checksums in a zarr archive."""

    def __init__(self, zarr_archive: ZarrArchive) -> None:
        self.zarr_archive = zarr_archive

    def modify(self, modifications: ZarrChecksumModificationQueue):
        while not modifications.empty:
            modification = modifications.pop_deepest()
            with ZarrChecksumFileUpdater(self.zarr_archive, modification.path) as file_updater:
                # Removing a checksum takes precedence over adding/modifying that checksum
                file_updater.add_checksums(modification.checksums_to_update)
                file_updater.remove_checksums(modification.paths_to_remove)

            # If we have reached the root node, then we obviously do not need to update the parent.
            if modification.path != Path('.') and modification.path != Path('/'):
                if file_updater.checksum_listing.checksums == []:
                    # We have removed all checksums from this checksum file.
                    # ZarrChecksumFileUpdater will have already deleted the checksum file, so all
                    # we need to do is queue this checksum for removal with it's parent.
                    modifications.queue_removal(modification.path.parent, modification.path)
                else:
                    # The parent needs to incorporate the checksum modification we just made.
                    modifications.queue_update(
                        modification.path.parent,
                        ZarrChecksum(
                            path=str(modification.path),
                            md5=file_updater.checksum_listing.md5,
                        ),
                    )

    def update_checksums(self, checksums: list[ZarrChecksum]):
        modifications = ZarrChecksumModificationQueue()
        for checksum in checksums:
            modifications.queue_update(Path(checksum.path).parent, checksum)
        self.modify(modifications)

    def remove_checksums(self, paths: list[str]):
        modifications = ZarrChecksumModificationQueue()
        for path in paths:
            modifications.queue_removal(Path(path).parent, path)
        self.modify(modifications)


# We do not store a checksum file for empty directories since an empty directory doesn't exist in
# S3. However, an empty zarr file still needs to have a checksum, even if it has no checksum file.
# For convenience, we define this constant as the "null" checksum.
EMPTY_CHECKSUM = ZarrJSONChecksumSerializer().generate_listing([]).md5
