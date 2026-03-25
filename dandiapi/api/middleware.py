from __future__ import annotations

from contextvars import ContextVar

from django.utils.deprecation import MiddlewareMixin
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

# Context variable for username
_current_username: ContextVar[str] = ContextVar('current_username', default='AnonymousUser')


class LoggingAuthenticationMixin:
    """Mixin that adds username logging to authentication classes."""

    def authenticate(self, request):
        """Authenticate and log username if successful."""
        result = super().authenticate(request)
        if result is not None:
            user, _token = result
            if user and user.is_authenticated:
                _current_username.set(user.username)
        return result


class LoggingOAuth2Authentication(LoggingAuthenticationMixin, OAuth2Authentication):
    """OAuth2 authentication that sets username for logging."""


class LoggingSessionAuthentication(LoggingAuthenticationMixin, SessionAuthentication):
    """Session authentication that sets username for logging."""


class LoggingTokenAuthentication(LoggingAuthenticationMixin, TokenAuthentication):
    """Token authentication that sets username for logging."""


class GunicornUsernameMiddleware(MiddlewareMixin):
    """
    Middleware to add username header for gunicorn access logs.

    This middleware adds a custom response header that can be logged
    by gunicorn's access log format to include the authenticated user's
    username in access logs.
    """

    def process_request(self, _request):
        """Initialize username as AnonymousUser at the start of request."""
        _current_username.set('AnonymousUser')

    def process_response(self, request, response):
        """Add username header after the request has been fully processed."""
        # Try to get the username from context variable first (set by DRF)
        username = _current_username.get()

        # Fallback to checking request.user if context variable wasn't set.
        if (
            username == 'AnonymousUser'
            and hasattr(request, 'user')
            and request.user.is_authenticated
        ):
            username = request.user.username
            _current_username.set(username)

        # Add username as a response header that gunicorn can log
        response['X-Request-Username'] = username

        return response
