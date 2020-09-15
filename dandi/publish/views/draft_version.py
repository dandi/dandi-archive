from django.contrib.auth.validators import UnicodeUsernameValidator
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_extensions.mixins import DetailSerializerMixin, NestedViewSetMixin

from dandi.publish.models import Dandiset, DraftVersion
from dandi.publish.tasks import publish_version
from dandi.publish.views.dandiset import DandisetSerializer


class UserSerializer(serializers.Serializer):
    username = serializers.CharField(
        min_length=1,
        max_length=150,
        help_text=('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[UnicodeUsernameValidator()],
    )


class DraftVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DraftVersion
        fields = [
            'dandiset',
            'name',
            'created',
            'modified',
            'locked',
            'locked_by',
        ]
        read_only_fields = ['created']

    dandiset = DandisetSerializer()
    locked_by = UserSerializer()


class DraftVersionDetailSerializer(DraftVersionSerializer):
    class Meta(DraftVersionSerializer.Meta):
        fields = DraftVersionSerializer.Meta.fields + ['metadata']


class DraftVersionViewSet(NestedViewSetMixin, DetailSerializerMixin, GenericViewSet):
    queryset = DraftVersion.objects.all().select_related('dandiset')
    queryset_detail = queryset

    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = DraftVersionSerializer
    serializer_detail_class = DraftVersionDetailSerializer

    def list(self, request, dandiset__pk):
        dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
        serializer = DraftVersionSerializer(dandiset.draft_version)
        return Response(serializer.data)

    @action(detail=False, methods=['POST'])
    def lock(self, request, dandiset__pk):
        dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
        dandiset.draft_version.lock(request.user)
        serializer = DraftVersionSerializer(dandiset.draft_version)
        return Response(serializer.data)

    @action(detail=False, methods=['POST'])
    def unlock(self, request, dandiset__pk):
        dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
        dandiset.draft_version.unlock(request.user)
        serializer = DraftVersionSerializer(dandiset.draft_version)
        return Response(serializer.data)

    @action(detail=False, methods=['POST'])
    def publish(self, request, dandiset__pk):
        dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
        # Locking will fail if the draft is currently locked
        # We want the draft to stay locked until publish completes or fails
        dandiset.draft_version.lock(request.user)
        publish_version.delay(dandiset.id, request.user.id)
        return Response('', status=status.HTTP_202_ACCEPTED)
