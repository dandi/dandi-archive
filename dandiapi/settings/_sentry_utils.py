from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentry_sdk._types import SamplingContext


def get_sentry_performance_sample_rate(sampling_context: SamplingContext) -> float:
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

        if 'wsgi_environ' in sampling_context:
            wsgi_environ = sampling_context['wsgi_environ']

            if wsgi_environ.get('REQUEST_METHOD') in ['GET', 'HEAD']:
                for route in noisy_route_regex:
                    if re.search(route, wsgi_environ.get('PATH_INFO', '')):
                        return True

        return False

    return 0.001 if is_noisy() else 0.01
