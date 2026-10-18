from __future__ import annotations

import typing

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from oauth2_provider import views as oauth2_views

if typing.TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.http import HttpRequest


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Allow access only to staff and superuser users, like ``IsAdminUser`` does for the API."""

    request: HttpRequest

    def test_func(self) -> bool:
        user = typing.cast('User', self.request.user)
        return user.is_staff or user.is_superuser


# django-oauth-toolkit ships self-service views that let any logged-in user register and
# manage OAuth2 applications. Registering an external application is an administrative
# action, so these subclasses restrict those views to admin users.
class ApplicationList(AdminRequiredMixin, oauth2_views.ApplicationList):
    pass


class ApplicationRegistration(AdminRequiredMixin, oauth2_views.ApplicationRegistration):
    pass


class ApplicationDetail(AdminRequiredMixin, oauth2_views.ApplicationDetail):
    pass


class ApplicationUpdate(AdminRequiredMixin, oauth2_views.ApplicationUpdate):
    pass


class ApplicationDelete(AdminRequiredMixin, oauth2_views.ApplicationDelete):
    pass
