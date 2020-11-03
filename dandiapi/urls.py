from django.conf import settings
from django.contrib import admin
from django.urls import include, path, register_converter
from drf_yasg2 import openapi
from drf_yasg2.views import get_schema_view
from rest_framework import permissions
from rest_framework_extensions.routers import ExtendedSimpleRouter

from dandiapi.api.views import (
    AssetViewSet,
    DandisetViewSet,
    VersionViewSet,
    search_view,
    stats_view,
)

router = ExtendedSimpleRouter()
(
    router.register(r'dandisets', DandisetViewSet, basename='dandiset')
    .register(
        r'versions',
        VersionViewSet,
        basename='version',
        parents_query_lookups=[f'dandiset__{DandisetViewSet.lookup_field}'],
    )
    .register(
        r'assets',
        AssetViewSet,
        basename='asset',
        parents_query_lookups=[
            f'version__dandiset__{DandisetViewSet.lookup_field}',
            f'version__{VersionViewSet.lookup_field}',
        ],
    )
)


schema_view = get_schema_view(
    openapi.Info(
        title='DANDI Archive',
        default_version='v1',
        description='The BRAIN Initiative archive for publishing and sharing '
        'cellular neurophysiology data',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


class DandisetIDConverter:
    regex = r'\d{6}'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(DandisetIDConverter, 'dandiset_id')
urlpatterns = [
    path('api/', include(router.urls)),
    path('api/search/', search_view),
    path('api/stats/', stats_view),
    # path(r'api/dandisets/<dandiset_id:dandiset__pk>/draft/', draft_view),
    # path(r'api/dandisets/<dandiset_id:dandiset__pk>/draft/lock/', draft_lock_view),
    # path(r'api/dandisets/<dandiset_id:dandiset__pk>/draft/unlock/', draft_unlock_view),
    # path(r'api/dandisets/<dandiset_id:dandiset__pk>/draft/publish/', draft_publish_view),
    # path(r'api/dandisets/<dandiset_id:dandiset__pk>/draft/owners/', draft_owners_view),
    path('admin/', admin.site.urls),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
