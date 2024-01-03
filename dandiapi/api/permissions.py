from __future__ import annotations
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated

from dandiapi.api.models.user import UserMetadata


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
