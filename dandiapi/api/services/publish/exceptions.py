from __future__ import annotations
from rest_framework import status

from dandiapi.api.services.exceptions import DandiError


class DandisetAlreadyPublishedError(DandiError):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'There have been no changes to the draft version since the last publish.'


class DandisetAlreadyPublishingError(DandiError):
    http_status_code = status.HTTP_423_LOCKED
    message = 'Dandiset is currently being published'


class DandisetBeingValidatedError(DandiError):
    http_status_code = status.HTTP_409_CONFLICT
    message = 'Dandiset is currently being validated'


class DandisetInvalidMetadataError(DandiError):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'Dandiset metadata or asset metadata is not valid'


class DandisetValidationPendingError(DandiError):
    http_status_code = status.HTTP_409_CONFLICT
    message = 'Metadata validation is pending for this dandiset, please try again later.'


class DandisetNotLockedError(DandiError):
    http_status_code = status.HTTP_409_CONFLICT
