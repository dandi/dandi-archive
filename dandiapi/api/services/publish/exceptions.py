from rest_framework import status

from dandiapi.api.services.exceptions import DandiException


class DandisetAlreadyPublished(DandiException):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'There have been no changes to the draft version since the last publish.'


class DandisetAlreadyPublishing(DandiException):
    http_status_code = status.HTTP_423_LOCKED
    message = 'Dandiset is currently being published'


class DandisetBeingValidated(DandiException):
    http_status_code = status.HTTP_409_CONFLICT
    message = 'Dandiset is currently being validated'


class DandisetInvalidMetadata(DandiException):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = 'Dandiset metadata or asset metadata is not valid'


class DandisetValidationPending(DandiException):
    http_status_code = status.HTTP_409_CONFLICT
    message = 'Metadata validation is pending for this dandiset, please try again later.'


class DandisetNotLocked(DandiException):
    http_status_code = status.HTTP_409_CONFLICT
