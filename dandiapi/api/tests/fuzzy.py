from __future__ import annotations

import re

from dandischema.conf import get_instance_config


class Re:
    def __init__(self, pattern):
        if isinstance(pattern, type(re.compile(''))):
            self.pattern = pattern
        else:
            self.pattern = re.compile(pattern)

    def __eq__(self, other):
        return self.pattern.fullmatch(other) is not None

    def __str__(self):
        return self.pattern.pattern

    def __repr__(self):
        return repr(self.pattern.pattern)

    def __hash__(self):
        return hash(self.pattern)


schema_config = get_instance_config()

TIMESTAMP_RE = Re(r'\d{4}-\d{2}-\d{2}T\d{2}\:\d{2}\:\d{2}\.\d{6}Z')
UTC_ISO_TIMESTAMP_RE = Re(r'\d{4}-\d{2}-\d{2}T\d{2}\:\d{2}\:\d{2}\.\d{6}\+[0-9]{2}:[0-9]{2}')
DATE_RE = Re(r'\d{4}-\d{2}-\d{2}')
DANDISET_ID_RE = Re(r'\d{6}')
DANDISET_SCHEMA_ID_RE = Re(rf'{schema_config.instance_name}:\d{{6}}')
VERSION_ID_RE = Re(r'0\.\d{6}\.\d{4}')
HTTP_URL_RE = Re(r'http[s]?\://[^/]+(/[^/]+)*[/]?(&.+)?')
UUID_RE = Re(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
URN_RE = Re(r'urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')

DEFAULT_WAS_ASSOCIATED_WITH = {
    'id': URN_RE,
    'identifier': schema_config.instance_identifier,
    'name': f'{schema_config.instance_name} API',
    'version': '0.1.0',
    'schemaKey': 'Software',
}
