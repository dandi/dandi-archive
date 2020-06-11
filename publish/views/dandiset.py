from django.http import Http404
from rest_framework import serializers
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet


from publish.models import Dandiset
from publish.tasks import sync_dandiset
from publish.views.common import DandiPagination


class DandisetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dandiset
        fields = [
            'identifier',
            'created',
            'updated',
        ]
        read_only_fields = ['created']


# class DandisetPublishSerializer(serializers.Serializer):
#     girder_id = serializers.CharField()
#     token = serializers.CharField(allow_blank=True, default='')


class DandisetViewSet(ReadOnlyModelViewSet):
    queryset = Dandiset.objects.all()

    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = DandisetSerializer
    pagination_class = DandiPagination

    lookup_value_regex = Dandiset.IDENTIFIER_REGEX
    # This is not strictly necessary (it defaults to 'pk'), but it clarifies
    # that the 'identifier' property should be used when forming URLs
    # TODO: Test how reverse URLs are created
    lookup_url_kwarg = 'identifier'

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

        sync_dandiset.delay(draft_folder_id)
        return Response('', status=status.HTTP_202_ACCEPTED)
