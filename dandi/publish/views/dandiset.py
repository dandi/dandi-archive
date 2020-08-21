from django.http import Http404
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from dandi.publish.girder import GirderClient
from dandi.publish.models import Dandiset
from dandi.publish.views.common import DandiPagination


class DandisetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dandiset
        fields = [
            'identifier',
            'created',
            'updated',
        ]
        read_only_fields = ['created']


class DandisetViewSet(ReadOnlyModelViewSet):
    queryset = Dandiset.objects.all()

    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = DandisetSerializer
    pagination_class = DandiPagination

    lookup_value_regex = Dandiset.IDENTIFIER_REGEX
    # This is to maintain consistency with the auto-generated names shown in swagger.
    lookup_url_kwarg = 'dandiset__pk'

    def get_object(self):
        # Alternative to path converters, which DRF doesn't support
        # https://docs.djangoproject.com/en/3.0/topics/http/urls/#registering-custom-path-converters

        lookup_url = self.kwargs[self.lookup_url_kwarg]
        try:
            lookup_value = int(lookup_url)
        except ValueError:
            raise Http404('Not a valid identifier.')
        self.kwargs[self.lookup_url_kwarg] = lookup_value

        return super().get_object()

    @action(detail=False, methods=['POST'])
    def sync(self, request):
        if 'folder-id' not in request.query_params:
            raise ValidationError('Missing query parameter "folder-id"')
        draft_folder_id = request.query_params['folder-id']

        with GirderClient() as client:
            Dandiset.from_girder(draft_folder_id, client)
        return Response('', status=status.HTTP_202_ACCEPTED)
