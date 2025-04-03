from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status

from dandiapi.api.services.exceptions import DandiError

if TYPE_CHECKING:
    from dandiapi.api.models.dandiset import DandisetPermissions


class DandisetPermRequiredError(DandiError):
    http_status_code = status.HTTP_403_FORBIDDEN

    def __init__(self, perm: DandisetPermissions) -> None:
        message = f'The {perm} permission is required for this action.'
        super().__init__(message=message)


class DraftDandisetNotModifiableError(DandiError):
    http_status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    message = 'Only draft versions can be modified.'


class AssetAlreadyExistsError(DandiError):
    http_status_code = status.HTTP_409_CONFLICT
    message = 'An asset with that path already exists'


class AssetPathConflictError(DandiError):
    http_status_code = status.HTTP_409_CONFLICT

    def __init__(self, new_path: str, existing_paths: list[str]) -> None:
        message = f'Path of new asset "{new_path}" conflicts with existing assets: {existing_paths}'
        super().__init__(message)


class ZarrArchiveBelongsToDifferentDandisetError(DandiError):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'The zarr archive belongs to a different dandiset'
