from __future__ import annotations

from rest_framework.throttling import UserRateThrottle


# This is not currently used, but if we ever choose to rate limit logged-in users,
# this is how we can accomplish that, without applying it to admins.
class DandiUserRateThrottle(UserRateThrottle):
    def get_cache_key(self, request, view):
        # Don't rate limit admin users
        if request.user and (request.user.is_staff or request.user.is_superuser):
            return None

        return super().get_cache_key(request, view)
