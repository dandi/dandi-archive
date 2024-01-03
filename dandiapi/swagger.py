# Separate from settings.py due to being a somewhat of a premature import there.
# See https://github.com/dandi/dandi-api/pull/482#issuecomment-901250541 .
from __future__ import annotations
from drf_yasg.inspectors import SwaggerAutoSchema


class DANDISwaggerAutoSchema(SwaggerAutoSchema):
    """Custom class for @swagger_auto_schema to provide summary from one line docstrings.

    See https://github.com/axnsan12/drf-yasg/issues/205 and
    https://github.com/axnsan12/drf-yasg/issues/265 for more information on why it is not
    a default behavior.
    """

    def split_summary_from_description(self, description):
        summary, description = super().split_summary_from_description(description)
        if summary is None:
            return description, None
        return summary, description
