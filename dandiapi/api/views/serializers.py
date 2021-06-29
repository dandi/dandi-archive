from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers

from dandiapi.api.models import Asset, AssetBlob, AssetMetadata, Dandiset, Version, VersionMetadata


# The default ModelSerializer for User fails if the user already exists
class UserSerializer(serializers.Serializer):
    username = serializers.CharField(validators=[UnicodeUsernameValidator()])


class UserDetailSerializer(serializers.Serializer):
    username = serializers.CharField(validators=[UnicodeUsernameValidator()])
    name = serializers.CharField(validators=[UnicodeUsernameValidator()])
    admin = serializers.BooleanField()


class DandisetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dandiset
        fields = [
            'identifier',
            'created',
            'modified',
        ]
        read_only_fields = ['created']


class VersionMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = VersionMetadata
        fields = ['metadata', 'name']
        # By default, validators contains a single UniqueTogether constraint.
        # This will fail serialization if the version metadata already exists,
        # which we do not want.
        validators = []


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
        fields = [
            'version',
            'name',
            'asset_count',
            'size',
            'status',
            'created',
            'modified',
            'dandiset',
        ]
        read_only_fields = ['created']

    dandiset = DandisetSerializer()
    # name = serializers.SlugRelatedField(read_only=True, slug_field='name')


class DandisetDetailSerializer(DandisetSerializer):
    class Meta(DandisetSerializer.Meta):
        fields = DandisetSerializer.Meta.fields + ['most_recent_published_version', 'draft_version']

    most_recent_published_version = VersionSerializer(read_only=True)
    draft_version = VersionSerializer(read_only=True)


class VersionDetailSerializer(VersionSerializer):
    class Meta(VersionSerializer.Meta):
        fields = VersionSerializer.Meta.fields + ['validation_error', 'metadata']

    metadata = serializers.SlugRelatedField(read_only=True, slug_field='metadata')
    status = serializers.CharField(source='publish_status')
    validation_error = serializers.CharField(source='publish_validation_error')


class AssetBlobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetBlob
        fields = [
            'blob_id',
            'etag',
            'sha256',
            'size',
        ]


class AssetMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetMetadata
        fields = ['metadata']


class AssetValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['status', 'validation_error']


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            'asset_id',
            'path',
            'size',
            'created',
            'modified',
        ]
        read_only_fields = ['created']


class AssetDetailSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        fields = AssetSerializer.Meta.fields + ['metadata']

    metadata = serializers.SlugRelatedField(read_only=True, slug_field='metadata')
