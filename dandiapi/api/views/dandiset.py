from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from guardian.shortcuts import assign_perm
from guardian.utils import get_40x_or_None
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.viewsets import ReadOnlyModelViewSet

from dandiapi.api.models import Dandiset, Version, VersionMetadata
from dandiapi.api.views.common import DandiPagination
from dandiapi.api.views.serializers import (
    DandisetSerializer,
    UserSerializer,
    VersionMetadataSerializer,
)


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

    @swagger_auto_schema(
        request_body=VersionMetadataSerializer(),
        responses={200: DandisetSerializer()},
    )
    def create(self, request):
        serializer = VersionMetadataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        version_metadata, created = VersionMetadata.objects.get_or_create(
            name=serializer.validated_data['name'],
            metadata=serializer.validated_data['metadata'],
        )
        if created:
            version_metadata.save()

        dandiset = Dandiset()
        dandiset.save()
        assign_perm('owner', request.user, dandiset)
        version = Version(dandiset=dandiset, metadata=version_metadata, version='draft')
        version.save()

        serializer = DandisetSerializer(instance=dandiset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(method='GET', responses={200: UserSerializer(many=True)})
    @swagger_auto_schema(
        method='PUT',
        request_body=UserSerializer(many=True),
        responses={200: UserSerializer(many=True)},
    )
    # TODO move these into a viewset
    @action(methods=['GET', 'PUT'], detail=True)
    def users(self, request, dandiset__pk):
        dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
        if request.method == 'PUT':
            # Verify that the user is currently an owner
            response = get_40x_or_None(request, ['owner'], dandiset, return_403=True)
            if response:
                return response

            serializer = UserSerializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)

            def get_user_or_400(username):
                try:
                    return User.objects.get(username=username)
                except User.DoesNotExist:
                    raise ValidationError(f'User {username} not found')

            owners = [
                get_user_or_400(username=owner['username']) for owner in serializer.validated_data
            ]
            if len(owners) < 1:
                raise ValidationError('Cannot remove all draft owners')

            dandiset.set_owners(owners)
            dandiset.save()
        serializer = UserSerializer(dandiset.owners, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
