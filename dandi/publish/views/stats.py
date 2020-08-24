from django.contrib.auth.models import User
from rest_framework.decorators import api_view
from rest_framework.response import Response

from dandi.publish.models import Asset, DraftVersion, Version


@api_view()
def stats_view(self):
    draft_count = DraftVersion.objects.count()
    published_count = Version.published_count()
    user_count = User.objects.count()
    species_count = 0  # TODO this needs to be added to the Version model
    subject_count = 0  # TODO this needs to be added to the Version model
    cell_count = 0  # TODO this needs to be added to the Version model
    size = Asset.total_size()
    return Response(
        {
            'draft_count': draft_count,
            'published_count': published_count,
            'user_count': user_count,
            'species_count': species_count,
            'subject_count': subject_count,
            'cell_count': cell_count,
            'size': size,
        }
    )
