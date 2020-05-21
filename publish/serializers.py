from rest_framework import serializers

from .models import Dandiset, NWBFile


class NWBFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = NWBFile
        fields = ['created', 'updated', 'name', 'size', 'sha256', 'metadata']


class DandisetSerializer(serializers.ModelSerializer):
    """Serializes a dandiset with all file information."""

    nwb_files = NWBFileSerializer(many=True)

    class Meta:
        model = Dandiset
        fields = ['created', 'updated', 'dandi_id', 'version', 'metadata', 'nwb_files']


class DandisetListSerializer(serializers.ModelSerializer):
    """Serializes a dandiset with only metadata (no files)."""

    class Meta:
        model = Dandiset
        fields = ['created', 'updated', 'dandi_id', 'version', 'metadata']


class DandisetPublishSerializer(serializers.Serializer):
    girder_id = serializers.CharField()
    token = serializers.CharField(allow_blank=True, default='')
