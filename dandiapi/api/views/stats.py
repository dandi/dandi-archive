from __future__ import annotations

from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from dandiapi.api.models.stats import ApplicationStats


class ApplicationStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationStats
        exclude = ['id', 'timestamp']


@api_view()
def stats_view(self):
    return Response(ApplicationStatsSerializer(ApplicationStats.objects.last()).data)
