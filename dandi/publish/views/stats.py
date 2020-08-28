from django.contrib.auth.models import User
from rest_framework.decorators import api_view
from rest_framework.response import Response

from dandi.publish.models import Asset, Dandiset, DraftVersion


@api_view()
def stats_view(self):
    draft_count = DraftVersion.objects.count()
    published_count = Dandiset.published_count()
    user_count = User.objects.count()
    size = Asset.total_size()
    return Response(
        {
            'draft_count': draft_count,
            'published_count': published_count,
            'user_count': user_count,
            'size': size,
        }
    )
