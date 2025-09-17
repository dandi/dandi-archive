from __future__ import annotations

from rest_framework.throttling import UserRateThrottle


class DandiUserRateThrottle(UserRateThrottle):
    def get_cache_key(self, request, view):
        # Don't rate limit admin users
        if request.user and (request.user.is_staff or request.user.is_superuser):
            return None

        return super().get_cache_key(request, view)
