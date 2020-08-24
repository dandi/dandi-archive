from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import JsonResponse
from rest_framework.viewsets import ViewSet

from dandi.publish.models import Asset, DraftVersion, Version


class StatsViewSet(ViewSet):
    def list(self, request):
        draft_count = DraftVersion.objects.count()
        published_count = Version.objects.values('dandiset').distinct().count()
        user_count = get_user_model().objects.count()
        species_count = 0  # TODO this needs to be added to the Version model
        subject_count = 0  # TODO this needs to be added to the Version model
        cell_count = 0  # TODO this needs to be added to the Version model
        size = Asset.objects.aggregate(size=Sum('size'))['size'] or 0
        return JsonResponse(
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
