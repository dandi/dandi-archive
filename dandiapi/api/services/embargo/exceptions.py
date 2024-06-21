from __future__ import annotations

from rest_framework import status

from dandiapi.api.services.exceptions import DandiError


class AssetBlobEmbargoedError(DandiError):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'This operation cannot be performed on embargoed assets blobs.'


class DandisetNotEmbargoedError(DandiError):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'Dandiset not embargoed'


class DandisetActiveUploadsError(DandiError):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'Dandiset unembargo not allowed with active uploads'


class DandisetUnembargoInProgressError(DandiError):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'Dandiset modification not allowed during unembargo'


class UnauthorizedEmbargoAccessError(DandiError):
    http_status_code = status.HTTP_401_UNAUTHORIZED
    message = (
        'Authentication credentials must be provided when attempting to access embargoed dandisets'
    )
