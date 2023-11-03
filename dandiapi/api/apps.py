from __future__ import annotations

import logging
import re

from django.apps import AppConfig
from django.conf import settings
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


class PublishConfig(AppConfig):
    name = 'dandiapi.api'
    verbose_name = 'DANDI: Publish'

    @staticmethod
    def _get_sentry_performance_sample_rate(*args, **kwargs) -> float:
        from dandiapi.api.models.asset import Asset
        from dandiapi.api.models.dandiset import Dandiset
        from dandiapi.api.models.version import Version

        def is_noisy():
            # these are noisy routes that we can reduce the sampling size for.
            # TODO: use the django url resolver to avoid redefining regular expressions.
            noisy_route_regex = [
                f'zarr/{Asset.UUID_REGEX}.zarr/[0-9/]+',
                f'assets/{Asset.UUID_REGEX}/download',
                (
                    f'dandisets/{Dandiset.IDENTIFIER_REGEX}/versions/{Version.VERSION_REGEX}/'
                    'assets/{Asset.UUID_REGEX}'
                ),
            ]

            if len(args) and 'wsgi_environ' in args[0]:
                wsgi_environ = args[0]['wsgi_environ']

                if wsgi_environ.get('REQUEST_METHOD') in ['GET', 'HEAD']:
                    for route in noisy_route_regex:
                        if re.search(route, wsgi_environ.get('PATH_INFO', '')):
                            return True

            return False

        return 0.001 if is_noisy() else 0.01

    def ready(self):
        import dandiapi.api.checks  # noqa: F401
        import dandiapi.api.signals  # noqa: F401

        if hasattr(settings, 'SENTRY_DSN'):
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.SENTRY_ENVIRONMENT,
                release=settings.SENTRY_RELEASE,
                integrations=[
                    LoggingIntegration(level=logging.INFO, event_level=logging.WARNING),
                    DjangoIntegration(),
                    CeleryIntegration(),
                ],
                # Only include dandiapi/ in the default stack trace
                in_app_include=['dandiapi'],
                # Send traces for non-exception events too
                attach_stacktrace=True,
                # Submit request User info from Django
                send_default_pii=True,
                traces_sampler=self._get_sentry_performance_sample_rate,
                profiles_sampler=self._get_sentry_performance_sample_rate,
            )
