from __future__ import annotations

from rest_framework import serializers

from dandiapi.api.models.asset import Asset
from dandiapi.api.models.asset_paths import AssetPath


class PathFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetPath
        fields = [
            'path',
            'total_assets',
            'total_size',
        ]

    path = serializers.CharField()
    total_assets = serializers.IntegerField(source='aggregate_files')
    total_size = serializers.IntegerField(source='aggregate_size')


class PathAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            'asset_id',
            'path',
            'created',
            'modified',
            'zarr',
            'blob',
            'metadata',
            'size',
        ]

    blob = serializers.UUIDField(source='blob.blob_id', allow_null=True)
    zarr = serializers.UUIDField(source='zarr.zarr_id', allow_null=True)

    def __init__(self, *args, include_metadata=False, **kwargs):
        if not include_metadata:
            del self.fields['metadata']

        super().__init__(*args, **kwargs)


class PathResultSerializer(serializers.Serializer):
    type = serializers.SerializerMethodField()
    resource = serializers.SerializerMethodField()

    def get_type(self, obj: AssetPath):
        if obj.asset is not None:
            return 'asset'
        return 'folder'

    def get_resource(self, obj: AssetPath):
        if obj.asset is not None:
            return PathAssetSerializer(obj.asset, include_metadata=self.context['metadata']).data
        return PathFolderSerializer(obj).data


class AtPathQuerySerializer(serializers.Serializer):
    dandiset_id = serializers.CharField()
    version_id = serializers.CharField()
    path = serializers.CharField(default='')
    metadata = serializers.BooleanField(default=False)
    children = serializers.BooleanField(default=False)
