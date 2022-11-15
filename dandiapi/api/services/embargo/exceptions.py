from rest_framework import status

from dandiapi.api.services.exceptions import DandiException


class AssetNotEmbargoed(DandiException):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'Only embargoed assets can be unembargoed.'


class DandisetNotEmbargoed(DandiException):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'Dandiset not embargoed'
