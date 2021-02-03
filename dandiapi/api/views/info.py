from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

schema_url = (
    'https://raw.githubusercontent.com/dandi/schema/master/'
    f'releases/{settings.DANDI_SCHEMA_VERSION}/dandiset.json'
)


@api_view()
def info_view(self):
    return Response(
        {
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
            'schemaURL': schema_url,
        }
    )
