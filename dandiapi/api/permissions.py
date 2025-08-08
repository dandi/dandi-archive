from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.request import Request

from dandiapi.api.models.user import UserMetadata

if TYPE_CHECKING:
    from django.contrib.auth.models import User


# https://github.com/typeddjango/django-stubs#how-can-i-create-a-httprequest-thats-guaranteed-to-have-an-authenticated-user
class AuthenticatedRequest(Request):
    """A DRF Request guaranteed to have an authenticated user."""

    user: User


class IsApproved(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_superuser
            # NOTE: The following line results in an extra SQL query for every request
            # that hits an endpoint protected by this permission class. We may want to
            # optimize this by creating a custom auth backend that uses Django's
            # select_related if performance becomes an issue.
            or request.user.metadata.status == UserMetadata.Status.APPROVED
        )


class IsApprovedOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or (
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                # NOTE: see note in IsApproved class, same thing applies here.
                or request.user.metadata.status == UserMetadata.Status.APPROVED
            )
        )
