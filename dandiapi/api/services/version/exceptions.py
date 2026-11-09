from __future__ import annotations

from rest_framework import status

from dandiapi.api.services.exceptions import DandiError


class DraftVersionPublishingError(DandiError):
    http_status_code = status.HTTP_423_LOCKED
    message = (
        'This dandiset is currently being published. '
        'Please try again once publishing has completed.'
    )
