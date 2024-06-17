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
    message = 'Dandiset un-embargo not allowed with active uploads'
