from __future__ import annotations

from rest_framework import status

from dandiapi.api.services.exceptions import DandiError


class AssetNotEmbargoedError(DandiError):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'Only embargoed assets can be unembargoed.'


class DandisetNotEmbargoedError(DandiError):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'Dandiset not embargoed'
