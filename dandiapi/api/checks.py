from __future__ import annotations

from django.conf import settings
from django.core.checks import Error, register

from dandiapi.api.datacite import DANDI_DOI_SETTINGS


@register()
def check_doi_settings(app_configs, **kwargs):
    any_doi_setting = any(setting is not None for setting, _ in DANDI_DOI_SETTINGS)
    if not any_doi_setting:
        # If no DOI settings are defined, DOIs will not be created on publish.
        return []
    errors = []
    for setting, name in DANDI_DOI_SETTINGS:
        if setting is None:
            errors.append(
                Error(
                    f'Setting {name} is not specified, but other DOI settings are.',
                    hint=f'Define {name} as an environment variable.',
                    obj=settings,
                )
            )
    return errors
