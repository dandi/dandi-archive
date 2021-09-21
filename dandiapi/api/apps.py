from django.apps import AppConfig


class PublishConfig(AppConfig):
    name = 'dandiapi.api'
    verbose_name = 'DANDI: Publish'

    def ready(self):
        import dandiapi.api.checks  # noqa: F401
        import dandiapi.api.signals  # noqa: F401
