from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from django.conf import settings

if TYPE_CHECKING:
    import datetime


class PublishableMetadataMixin:
    @classmethod
    def published_by(cls, now: datetime.datetime):
        instance_identifier = settings.DANDI_SCHEMA_INSTANCE_CONFIG.instance_identifier

        return {
            'id': uuid4().urn,
            'name': 'DANDI publish',
            'startDate': now.isoformat(),
            # TODO: https://github.com/dandi/dandi-api/issues/465
            # endDate needs to be defined before publish is complete
            'endDate': now.isoformat(),
            'wasAssociatedWith': [
                {
                    'id': uuid4().urn,
                    **({'identifier': instance_identifier} if instance_identifier else {}),
                    'name': 'DANDI API',
                    # TODO: version the API
                    'version': '0.1.0',
                    'schemaKey': 'Software',
                }
            ],
            'schemaKey': 'PublishActivity',
        }
