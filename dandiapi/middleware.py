from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class DandiUserLoggingMiddleware:
    """
    Middleware to log user access information.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            username = request.user.username
            logger.info(f"User '{username}' accessed {request.path}")
        else:
            logger.info(f'Anonymous user accessed {request.path}')
        response = self.get_response(request)
        return response
