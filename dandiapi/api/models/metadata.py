from __future__ import annotations

import importlib
from typing import TYPE_CHECKING
from uuid import uuid4

from dandischema.conf import get_instance_config

if TYPE_CHECKING:
    import datetime

_SCHEMA_INSTANCE_CONFIG = get_instance_config()


class PublishableMetadataMixin:
    @classmethod
    def published_by(cls, now: datetime.datetime):
        instance_name = _SCHEMA_INSTANCE_CONFIG.instance_name
        instance_identifier = _SCHEMA_INSTANCE_CONFIG.instance_identifier

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
                    'name': f'{instance_name} API',
                    # TODO: version the API
                    'version': importlib.metadata.version('dandiapi'),
                    'schemaKey': 'Software',
                }
            ],
            'schemaKey': 'PublishActivity',
        }
