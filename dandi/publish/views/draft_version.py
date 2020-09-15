from django.contrib.auth.models import User
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from guardian.decorators import permission_required_or_403
from guardian.shortcuts import assign_perm, get_users_with_perms, remove_perm
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

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
    method='POST', request_body=UserSerializer(many=True),
)
@api_view(['POST'])
@permission_required_or_403('owner', (DraftVersion, 'dandiset__pk', 'dandiset__pk'))
@permission_classes([IsAuthenticatedOrReadOnly])
def draft_owners_view(request, dandiset__pk):
    draft_version = get_object_or_404(Dandiset, pk=dandiset__pk).draft_version

    new_owners_serializer = UserSerializer(data=request.data, many=True)
    if not new_owners_serializer.is_valid():
        return Response(new_owners_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    new_owners = [
        get_object_or_404(User, username=owner['username'])
        for owner in new_owners_serializer.validated_data
    ]
    if len(new_owners) < 1:
        return Response('Cannot remove all draft owners', status=status.HTTP_400_BAD_REQUEST)
    old_owners = get_users_with_perms(draft_version, only_with_perms_in=['owner'])

    # Remove old owners
    for old_owner in old_owners:
        if old_owner not in new_owners:
            remove_perm('owner', old_owner, draft_version)
    # Add new owners
    for new_owner in new_owners:
        if new_owner not in old_owners:
            assign_perm('owner', new_owner, draft_version)

    return Response('', status=status.HTTP_204_NO_CONTENT)
