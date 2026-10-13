from __future__ import annotations

import logging

from redis import RedisError
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle, UserRateThrottle

logger = logging.getLogger(__name__)


class FailOpenRateThrottle(SimpleRateThrottle):
    """
    A throttle which allows requests through when its cache backend is unreachable.

    Rate limiting protects the archive from excessive request volume, but it isn't itself a
    prerequisite for serving a request. Since the cache is consulted on every request, an
    unreachable cache server would otherwise fail every request, so instead degrade to not
    rate limiting at all.
    """

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except RedisError:
            logger.exception('Rate limit cache unavailable, allowing request')
            return True


class DandiAnonRateThrottle(FailOpenRateThrottle, AnonRateThrottle):
    pass


# This is not currently used, but if we ever choose to rate limit logged-in users,
# this is how we can accomplish that, without applying it to admins.
class DandiUserRateThrottle(FailOpenRateThrottle, UserRateThrottle):
    def get_cache_key(self, request, view):
        # Don't rate limit admin users
        if request.user and (request.user.is_staff or request.user.is_superuser):
            return None

        return super().get_cache_key(request, view)
