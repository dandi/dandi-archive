from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path, register_converter
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_extensions.routers import ExtendedSimpleRouter

from dandiapi.api.views import (
    AssetViewSet,
    DandisetViewSet,
    VersionViewSet,
    auth_token_view,
    blob_read_view,
    info_view,
    stats_view,
    upload_complete_view,
    upload_initialize_view,
    upload_validate_view,
    users_me_view,
    users_search_view,
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
            f'versions__dandiset__{DandisetViewSet.lookup_field}',
            f'versions__{VersionViewSet.lookup_field}',
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
    path('api/auth/token/', auth_token_view, name='auth-token'),
    path('api/stats/', stats_view),
    path('api/info/', info_view),
    path('api/blobs/digest/', blob_read_view, name='blob-read'),
    path('api/uploads/initialize/', upload_initialize_view, name='upload-initialize'),
    re_path(
        r'api/uploads/(?P<uuid>[0-9a-f\-]{36})/complete/',
        upload_complete_view,
        name='upload-complete',
    ),
    re_path(
        r'^api/uploads/(?P<uuid>[0-9a-f\-]{36})/validate/$',
        upload_validate_view,
        name='upload-validate',
    ),
    path('api/users/me/', users_me_view),
    path('api/users/search/', users_search_view),
    path('accounts/', include('allauth.urls')),
    path('admin/', admin.site.urls),
    path('oauth/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
