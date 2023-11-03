from __future__ import annotations

from django.conf import settings
from django.shortcuts import render


def root_content_view(request):
    return render(request, 'api/root_content.html', {'web_app_url': settings.DANDI_WEB_APP_URL})
