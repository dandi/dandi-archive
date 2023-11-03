from __future__ import annotations

from django.contrib.auth.models import User
from django.views.decorators.cache import cache_page
from rest_framework.decorators import api_view
from rest_framework.response import Response

from dandiapi.api.models import Asset, Dandiset


# Cache this response for 12 hours
@cache_page(60 * 60 * 12)
@api_view()
def stats_view(self):
    dandiset_count = Dandiset.objects.count()
    published_dandiset_count = Dandiset.published_count()
    user_count = User.objects.count()
    size = Asset.total_size()
    return Response(
        {
            'dandiset_count': dandiset_count,
            'published_dandiset_count': published_dandiset_count,
            'user_count': user_count,
            'size': size,
        }
    )
