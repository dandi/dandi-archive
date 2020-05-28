from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from rest_framework_extensions.routers import ExtendedSimpleRouter

from publish.views import AssetViewSet, DandisetViewSet, VersionViewSet


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

urlpatterns = [
    path('api/', include(router.urls)),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
