from rest_framework import status

from dandiapi.api.services.exceptions import DandiException


class DandisetAlreadyExists(DandiException):
    http_status_code = status.HTTP_400_BAD_REQUEST
