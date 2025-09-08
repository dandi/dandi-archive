from __future__ import annotations

from contextvars import ContextVar
import json
from typing import TYPE_CHECKING

from rich.logging import RichHandler

if TYPE_CHECKING:
    import logging

    from rich.console import ConsoleRenderable

# Use of a ContextVar is suggested by the Python logging cookbook
# https://docs.python.org/3/howto/logging-cookbook.html#use-of-contextvars
current_user: ContextVar[str | None] = ContextVar('current_user', default=None)


class RequestUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # If user was authenticated, store the request.user object for later use by the logger
        current_user.set(
            request.user.username
            if hasattr(request, 'user') and request.user.is_authenticated
            else 'AnonymousUser'
        )

        return response


class DandiHandler(RichHandler):
    def render_message(self, record: logging.LogRecord, message: str) -> ConsoleRenderable:
        username = current_user.get()
        if username:
            message = f'{message} {json.dumps({'username': username})}'
        return super().render_message(record, message)
