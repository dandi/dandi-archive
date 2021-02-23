from django.contrib.postgres.search import SearchVector
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from dandiapi.api.models import Version
from dandiapi.api.views.version import VersionSerializer


@swagger_auto_schema(
    method='GET',
    manual_parameters=[
        openapi.Parameter(
            'search',
            openapi.IN_QUERY,
            description='Search published dandisets',
            type=openapi.TYPE_STRING,
        )
    ],
)
@api_view()
def search_view(request):
    if 'search' not in request.query_params:
        return Response([])

    versions = Version.objects.annotate(search=SearchVector('metadata__metadata')).filter(
        search=request.query_params['search']
    )

    return Response(VersionSerializer(versions, many=True).data)
