from __future__ import annotations
from rest_framework import status


class DandiError(Exception):
    message: str | None
    http_status_code: int | None

    def __init__(
        self, message: str | None = None, http_status_code: int | None = None, *args: object
    ) -> None:
        self.message = message or self.message
        self.http_status_code = http_status_code or self.http_status_code

        super().__init__(*args)


class NotAllowedError(DandiError):
    message = 'Action not allowed'
    http_status_code = status.HTTP_403_FORBIDDEN


class AdminOnlyOperationError(DandiError):
    pass
