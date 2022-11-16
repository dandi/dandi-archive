from rest_framework import status

from dandiapi.api.services.exceptions import DandiException


class DandisetOwnerRequired(DandiException):
    http_status_code = status.HTTP_403_FORBIDDEN


class DraftDandisetNotModifiable(DandiException):
    http_status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    message = 'Only draft versions can be modified.'


class AssetAlreadyExists(DandiException):
    http_status_code = status.HTTP_409_CONFLICT
    message = 'An asset with that path already exists'


class AssetPathConflict(DandiException):
    http_status_code = status.HTTP_409_CONFLICT

    def __init__(self, new_path: str, existing_paths: list[str]) -> None:
        message = f'Path of new asset "{new_path}" conflicts with existing assets: {existing_paths}'
        super().__init__(message)


class ZarrArchiveBelongsToDifferentDandiset(DandiException):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'The zarr archive belongs to a different dandiset'
