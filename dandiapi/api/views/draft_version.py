from django.contrib.auth.models import User
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from guardian.decorators import permission_required_or_403
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from dandiapi.api.models import Dandiset, DraftVersion
from dandiapi.api.tasks import publish_version
from dandiapi.api.views.dandiset import DandisetSerializer


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
            'owners',
        ]
        read_only_fields = ['created']

    dandiset = DandisetSerializer()
    locked_by = UserSerializer()
    owners = UserSerializer(many=True)


class DraftVersionDetailSerializer(DraftVersionSerializer):
    class Meta(DraftVersionSerializer.Meta):
        fields = DraftVersionSerializer.Meta.fields + ['metadata']


@api_view()
@permission_classes([IsAuthenticatedOrReadOnly])
def draft_view(request, dandiset__pk):
    dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
    serializer = DraftVersionDetailSerializer(dandiset.draft_version)
    return Response(serializer.data)


@api_view(['POST'])
@permission_required_or_403('owner', (DraftVersion, 'dandiset__pk', 'dandiset__pk'))
@permission_classes([IsAuthenticatedOrReadOnly])
def draft_lock_view(request, dandiset__pk):
    dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
    dandiset.draft_version.lock(request.user)
    dandiset.draft_version.save()
    serializer = DraftVersionSerializer(dandiset.draft_version)
    return Response(serializer.data)


# Ownership is not required to unlock
# A user might be removed from the owners list while still having the lock
@api_view(['POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def draft_unlock_view(request, dandiset__pk):
    dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
    dandiset.draft_version.unlock(request.user)
    dandiset.draft_version.save()
    serializer = DraftVersionSerializer(dandiset.draft_version)
    return Response(serializer.data)


@api_view(['POST'])
@permission_required_or_403('owner', (DraftVersion, 'dandiset__pk', 'dandiset__pk'))
@permission_classes([IsAuthenticatedOrReadOnly])
def draft_publish_view(request, dandiset__pk):
    dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
    # Locking will fail if the draft is currently locked
    # We want the draft to stay locked until publish completes or fails
    dandiset.draft_version.lock(request.user)
    publish_version.delay(dandiset.id, request.user.id)
    return Response(status=status.HTTP_204_NO_CONTENT)


@swagger_auto_schema(
    method='POST',
    request_body=UserSerializer(many=True),
)
@api_view(['POST'])
@permission_required_or_403('owner', (DraftVersion, 'dandiset__pk', 'dandiset__pk'))
@permission_classes([IsAuthenticatedOrReadOnly])
def draft_owners_view(request, dandiset__pk):
    draft_version = get_object_or_404(Dandiset, pk=dandiset__pk).draft_version

    owners_serializer = UserSerializer(data=request.data, many=True)
    owners_serializer.is_valid(raise_exception=True)

    def get_user_or_400(username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError(f'User {username} not found')

    owners = [
        get_user_or_400(username=owner['username']) for owner in owners_serializer.validated_data
    ]
    if len(owners) < 1:
        raise ValidationError('Cannot remove all draft owners')

    draft_version.set_owners(owners)

    return Response(status=status.HTTP_204_NO_CONTENT)
