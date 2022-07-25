import logging

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
        """
        Determine sample rate of sentry performance.

        Only sample 1% of requests for performance monitoring, and significantly
        fewer for backups2datalad since it's particularly noisy.
        """
        if len(args) and 'wsgi_environ' in args[0]:
            if 'backups2datalad' in args[0]['wsgi_environ']['HTTP_USER_AGENT']:
                return 0.001

        return 0.01

    def ready(self):
        import dandiapi.api.checks  # noqa: F401
        import dandiapi.api.signals  # noqa: F401

        if hasattr(settings, 'SENTRY_DSN'):
            sentry_sdk.init(
                # If a "dsn" is not explicitly passed, sentry_sdk will attempt to find the DSN in
                # the SENTRY_DSN environment variable; however, by pulling it from an explicit
                # setting, it can be overridden by downstream project settings.
                dsn=settings.SENTRY_DSN,
                environment=settings.SENTRY_ENVIRONMENT,
                release=settings.SENTRY_RELEASE,
                integrations=[
                    LoggingIntegration(level=logging.INFO, event_level=logging.WARNING),
                    DjangoIntegration(),
                    CeleryIntegration(),
                ],
                # Send traces for non-exception events too
                attach_stacktrace=True,
                # Submit request User info from Django
                send_default_pii=True,
                traces_sampler=self._get_sentry_performance_sample_rate,
            )
