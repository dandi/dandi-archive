from __future__ import annotations

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path, register_converter, reverse_lazy
from django.views.generic import RedirectView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from dandiapi.api.models import Asset, Dandiset, Version
from dandiapi.api.views import (
    DashboardView,
    asset_audit_events,
    asset_download_view,
    asset_info_view,
    asset_view,
    auth_token_view,
    authorize_view,
    blob_read_view,
    dandiset_detail_view,
    dandiset_list_view,
    dandiset_search_view,
    dandiset_star_view,
    dandiset_unembargo_view,
    dandiset_uploads_view,
    dandiset_users_view,
    info_view,
    mailchimp_csv_view,
    robots_txt_view,
    root_content_view,
    schema_list_view,
    schema_view,
    stats_view,
    upload_complete_view,
    upload_initialize_view,
    upload_validate_view,
    user_approval_view,
    user_questionnaire_form_view,
    users_list_view,
    users_me_view,
    users_search_view,
    version_asset_download_view,
    version_asset_info_view,
    version_asset_paths_view,
    version_asset_validation_view,
    version_asset_view,
    version_assets_view,
    version_detail_view,
    version_info_view,
    version_list_view,
    version_publish_view,
    webdav,
)
from dandiapi.search.views import search_genotypes, search_species
from dandiapi.zarr.models import ZarrArchive
from dandiapi.zarr.views import zarr_files_view, zarr_finalize_view, zarr_list_view, zarr_view

# URL path fragments for the resource identifiers that appear in API paths. Assets and
# versions are addressable both on their own and underneath the version they belong to, and
# the nested forms name their path variables after the query lookups that reach them, since
# that is how they appear in the published API documentation.
DANDISET_PK = rf'(?P<dandiset__pk>{Dandiset.IDENTIFIER_REGEX})'
VERSION = rf'(?P<version>{Version.VERSION_REGEX})'
VERSIONS_DANDISET_PK = rf'(?P<versions__dandiset__pk>{Dandiset.IDENTIFIER_REGEX})'
VERSIONS_VERSION = rf'(?P<versions__version>{Version.VERSION_REGEX})'
ASSET_ID = rf'(?P<asset_id>{Asset.UUID_REGEX})'
ZARR_ID = rf'(?P<zarr_id>{ZarrArchive.UUID_REGEX})'

dandiset_urlpatterns = [
    path('dandisets/', dandiset_list_view, name='dandiset-list'),
    path('dandisets/search/', dandiset_search_view, name='dandiset-search'),
    re_path(rf'^dandisets/{DANDISET_PK}/$', dandiset_detail_view, name='dandiset-detail'),
    re_path(rf'^dandisets/{DANDISET_PK}/star/$', dandiset_star_view, name='dandiset-star'),
    re_path(
        rf'^dandisets/{DANDISET_PK}/unembargo/$',
        dandiset_unembargo_view,
        name='dandiset-unembargo',
    ),
    re_path(rf'^dandisets/{DANDISET_PK}/uploads/$', dandiset_uploads_view, name='dandiset-uploads'),
    re_path(rf'^dandisets/{DANDISET_PK}/users/$', dandiset_users_view, name='dandiset-users'),
]

version_urlpatterns = [
    re_path(
        rf'^dandisets/{DANDISET_PK}/versions/$',
        version_list_view,
        name='dandiset-version-list',
    ),
    re_path(
        rf'^dandisets/{DANDISET_PK}/versions/{VERSION}/$',
        version_detail_view,
        name='dandiset-version-detail',
    ),
    re_path(
        rf'^dandisets/{DANDISET_PK}/versions/{VERSION}/info/$',
        version_info_view,
        name='dandiset-version-info',
    ),
    re_path(
        rf'^dandisets/{DANDISET_PK}/versions/{VERSION}/publish/$',
        version_publish_view,
        name='dandiset-version-publish',
    ),
]

asset_urlpatterns = [
    re_path(rf'^assets/{ASSET_ID}/$', asset_view, name='asset-detail'),
    re_path(rf'^assets/{ASSET_ID}/download/$', asset_download_view, name='asset-download'),
    re_path(rf'^assets/{ASSET_ID}/info/$', asset_info_view, name='asset-info'),
    re_path(
        rf'^dandisets/{VERSIONS_DANDISET_PK}/versions/{VERSIONS_VERSION}/assets/$',
        version_assets_view,
        name='dandiset-version-asset-list',
    ),
    re_path(
        rf'^dandisets/{VERSIONS_DANDISET_PK}/versions/{VERSIONS_VERSION}/assets/paths/$',
        version_asset_paths_view,
        name='dandiset-version-asset-paths',
    ),
    re_path(
        rf'^dandisets/{VERSIONS_DANDISET_PK}/versions/{VERSIONS_VERSION}/assets/{ASSET_ID}/$',
        version_asset_view,
        name='dandiset-version-asset-detail',
    ),
    re_path(
        rf'^dandisets/{VERSIONS_DANDISET_PK}/versions/{VERSIONS_VERSION}'
        rf'/assets/{ASSET_ID}/download/$',
        version_asset_download_view,
        name='dandiset-version-asset-download',
    ),
    re_path(
        rf'^dandisets/{VERSIONS_DANDISET_PK}/versions/{VERSIONS_VERSION}'
        rf'/assets/{ASSET_ID}/info/$',
        version_asset_info_view,
        name='dandiset-version-asset-info',
    ),
    re_path(
        rf'^dandisets/{VERSIONS_DANDISET_PK}/versions/{VERSIONS_VERSION}'
        rf'/assets/{ASSET_ID}/validation/$',
        version_asset_validation_view,
        name='dandiset-version-asset-validation',
    ),
]

zarr_urlpatterns = [
    path('zarr/', zarr_list_view, name='zarr-list'),
    re_path(rf'^zarr/{ZARR_ID}/$', zarr_view, name='zarr-detail'),
    re_path(rf'^zarr/{ZARR_ID}/files/$', zarr_files_view, name='zarr-files'),
    re_path(rf'^zarr/{ZARR_ID}/finalize/$', zarr_finalize_view, name='zarr-finalize'),
]

# All core API endpoints
api_urlpatterns = [
    path(
        'api/',
        include(
            [
                *dandiset_urlpatterns,
                *version_urlpatterns,
                *asset_urlpatterns,
                *zarr_urlpatterns,
            ]
        ),
    ),
    path('api/auth/token/', auth_token_view, name='auth-token'),
    path('api/stats/', stats_view),
    path('api/info/', info_view),
    path('api/blobs/digest/', blob_read_view, name='blob-read'),
    path('api/schemas/available/', schema_list_view, name='schema-list-view'),
    path('api/schemas/', schema_view, name='schema-view'),
    path('api/uploads/initialize/', upload_initialize_view, name='upload-initialize'),
    re_path(
        r'api/uploads/(?P<upload_id>[0-9a-f\-]{36})/complete/',
        upload_complete_view,
        name='upload-complete',
    ),
    re_path(
        r'^api/uploads/(?P<upload_id>[0-9a-f\-]{36})/validate/$',
        upload_validate_view,
        name='upload-validate',
    ),
    path('api/users/me/', users_me_view),
    path('api/users/search/', users_search_view),
    path('api/users/', users_list_view),
    path('api/users/questionnaire-form/', user_questionnaire_form_view, name='user-questionnaire'),
    path('api/search/genotypes/', search_genotypes),
    path('api/search/species/', search_species),
]
schema_view = get_schema_view(
    openapi.Info(
        title='DANDI Archive',
        default_version='v1',
        description='The BRAIN Initiative archive for publishing and sharing '
        'cellular neurophysiology data',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=api_urlpatterns,
)

# Webdav only endpoints
webdav_urlpatterns = [
    path('api/webdav/assets/atpath/', webdav.atpath),
]
webdav_schema_view = get_schema_view(
    openapi.Info(
        title='Webdav API',
        default_version='v1',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=webdav_urlpatterns,
)


class DandisetIDConverter:
    regex = r'\d{6}'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(DandisetIDConverter, 'dandiset_id')
urlpatterns = [
    path('', root_content_view),
    path('robots.txt', robots_txt_view, name='robots_txt'),
    path('api/audit/events/asset', asset_audit_events, name='asset_audit_events'),
    *api_urlpatterns,
    *webdav_urlpatterns,
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('dashboard/', DashboardView.as_view(), name='dashboard-index'),
    path('dashboard/user/<str:username>/', user_approval_view, name='user-approval'),
    path('dashboard/mailchimp/', mailchimp_csv_view, name='mailchimp-csv'),
    # this url overrides the authorize url in oauth2_provider.urls to
    # support our user signup workflow
    path('oauth/authorize/', authorize_view, name='authorize'),
    path('oauth/', include('oauth2_provider.urls')),
    # Doc page views
    path('api/docs/redoc/', schema_view.with_ui('redoc'), name='docs-redoc'),
    path('api/docs/swagger/', schema_view.with_ui('swagger'), name='docs-swagger'),
    # Doc page redirects for backwards compatibility
    path(
        'swagger/',
        RedirectView.as_view(permanent=True, url=reverse_lazy('docs-swagger')),
        name='schema-swagger-ui',
    ),
    path(
        'redoc/',
        RedirectView.as_view(permanent=True, url=reverse_lazy('docs-redoc')),
        name='schema-redoc',
    ),
    # Webdav doc page views
    path(
        'api/webdav/docs/swagger/',
        webdav_schema_view.with_ui('swagger', cache_timeout=0),
        name='webdav-schema-swagger-ui',
    ),
]

if settings.DEBUG:
    import debug_toolbar.toolbar

    urlpatterns += [
        *debug_toolbar.toolbar.debug_toolbar_urls(),
        path('__reload__/', include('django_browser_reload.urls')),
    ]
