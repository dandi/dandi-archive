from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers

from dandiapi.api.models import (
    Asset,
    AssetBlob,
    AssetMetadata,
    Dandiset,
    Validation,
    Version,
    VersionMetadata,
)


# The default ModelSerializer for User fails if the user already exists
class UserSerializer(serializers.Serializer):
    username = serializers.CharField(validators=[UnicodeUsernameValidator()])


class UserDetailSerializer(serializers.Serializer):
    username = serializers.CharField(validators=[UnicodeUsernameValidator()])
    first_name = serializers.CharField(validators=[UnicodeUsernameValidator()])
    last_name = serializers.CharField(validators=[UnicodeUsernameValidator()])
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
            'created',
            'modified',
            'dandiset',
        ]
        read_only_fields = ['created']

    dandiset = DandisetSerializer()
    # name = serializers.SlugRelatedField(read_only=True, slug_field='name')


class VersionDetailSerializer(VersionSerializer):
    class Meta(VersionSerializer.Meta):
        fields = VersionSerializer.Meta.fields + ['metadata']

    metadata = serializers.SlugRelatedField(read_only=True, slug_field='metadata')


class AssetBlobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetBlob
        fields = [
            'uuid',
            'path',
            'sha256',
            'size',
        ]


class AssetMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetMetadata
        fields = ['metadata']


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            'uuid',
            'path',
            'sha256',
            'size',
            'created',
            'modified',
            'version',
        ]
        read_only_fields = ['created']

    version = VersionSerializer()


class AssetDetailSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        fields = AssetSerializer.Meta.fields + ['metadata']

    metadata = serializers.SlugRelatedField(read_only=True, slug_field='metadata')


class ValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Validation
        fields = [
            'state',
            'sha256',
            'created',
            'modified',
        ]


class ValidationErrorSerializer(serializers.ModelSerializer):
    class Meta(ValidationSerializer.Meta):
        fields = ValidationSerializer.Meta.fields + ['error']
