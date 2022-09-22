from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler


def rewrap_django_core_exceptions(exc: Exception, ctx: dict) -> Response | None:
    """
    Rewraps core Django exceptions and re-raises them as the DRF equivalent.

    This is useful for allowing internal APIs to throw Django validation errors
    and be used from DRF endpoints.
    """
    if isinstance(exc, DjangoValidationError):
        exc = drf_exceptions.ValidationError(as_serializer_error(exc))

    if isinstance(exc, Http404):
        exc = drf_exceptions.NotFound()

    if isinstance(exc, DjangoPermissionDenied):
        exc = drf_exceptions.PermissionDenied()

    response = exception_handler(exc, ctx)

    return response
