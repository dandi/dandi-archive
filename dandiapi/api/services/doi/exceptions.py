from __future__ import annotations

from rest_framework import status

from dandiapi.api.services.exceptions import DandiError


class DataCiteNotConfiguredError(DandiError):
    message = 'DataCite API is not configured'
    http_status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class DataCiteAPIError(DandiError):
    message = 'DataCite API request failed'
    http_status_code = status.HTTP_502_BAD_GATEWAY


class DataCitePublishNotEnabledError(DandiError):
    message = 'DataCite publish operations are not enabled'
    http_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class VersionDOIMissingError(DandiError):
    message = 'DOI dependency operations called on a Version without a DOI'
    http_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class DOIOperationNotPermittedError(DandiError):
    message = 'This DOI operation is not permitted for the specified Dandiset and/or Version.'
    http_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
