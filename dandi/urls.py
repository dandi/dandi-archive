from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers

from publish.api import DandisetViewSet

router = routers.DefaultRouter()
router.register('dandisets', DandisetViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
