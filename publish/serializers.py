from rest_framework import serializers

from .models import Asset, Dandiset, Version


class DandisetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dandiset
        fields = [
            'identifier',
            'created',
            'updated',
        ]
        read_only_fields = ['created']


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
        fields = [
            'dandiset',
            'version',
            'created',
            'updated',
        ]
        read_only_fields = ['created']

    dandiset = DandisetSerializer()


class VersionDetailSerializer(VersionSerializer):
    class Meta(VersionSerializer.Meta):
        fields = VersionSerializer.Meta.fields + ['metadata']


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            'version',
            'uuid',
            'path',
            'size',
            'sha256',
            'created',
            'updated',
        ]
        read_only_fields = ['created']

    version = VersionSerializer()


class AssetDetailSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        fields = AssetSerializer.Meta.fields + ['metadata']


# class DandisetPublishSerializer(serializers.Serializer):
#     girder_id = serializers.CharField()
#     token = serializers.CharField(allow_blank=True, default='')
