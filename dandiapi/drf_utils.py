from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)
from django.http import Http404
from rest_framework import exceptions as drf_exceptions, status
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler

from dandiapi.api.services.exceptions import DandiException


def rewrap_django_core_exceptions(exc: Exception, ctx: dict) -> Response | None:
    """
    Rewraps core Django exceptions and re-raises them as the DRF equivalent.

    This is useful for allowing internal APIs to throw Django validation errors
    and be used from DRF endpoints.
    """
    if isinstance(exc, DjangoValidationError):
        if len(exc.error_list) == 1:
            # Dandi returns validation errors with 1 problem as a raw
            # message. Support this for now, consider using the DRF enveloped format in the future.
            return Response(exc.error_list[0].message, status=status.HTTP_400_BAD_REQUEST)
        else:
            exc = drf_exceptions.ValidationError(as_serializer_error(exc))
    elif isinstance(exc, DandiException):
        return Response(exc.message, status=exc.http_status_code or status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, Http404):
        exc = drf_exceptions.NotFound()

    if isinstance(exc, DjangoPermissionDenied):
        # Dandi currently returns 403 with messages that aren't in an envelope (see above
        # for similarties with 400 errors). Prevent DRF from wrapping these messages and consider
        # switching in the future.
        if exc.args:
            return Response(exc.args[0], status=status.HTTP_403_FORBIDDEN)
        exc = drf_exceptions.PermissionDenied()

    return exception_handler(exc, ctx)
