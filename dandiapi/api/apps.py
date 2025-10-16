from __future__ import annotations

from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'dandiapi.api'
    verbose_name = 'DANDI Archive: API'

    def ready(self):
        # RUF100 is caused by https://github.com/astral-sh/ruff/issues/60
        import dandiapi.api.checks  # noqa: F401, RUF100
        import dandiapi.api.signals  # noqa: F401
