from rest_framework import serializers

from .models import Dandiset, NWBFile, Subject


class NWBFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = NWBFile
        fields = ['created', 'updated', 'subject',
                  'name', 'size', 'sha256', 'metadata']


class SubjectSerializer(serializers.ModelSerializer):
    nwb_files = NWBFileSerializer(many=True)

    class Meta:
        model = Subject
        fields = ['created', 'updated', 'name', 'metadata', 'nwb_files']


class DandisetSerializer(serializers.ModelSerializer):
    """
    Serializes a dandiset with all subject/file information
    """
    subjects = SubjectSerializer(many=True)

    class Meta:
        model = Dandiset
        fields = ['created', 'updated', 'dandi_id',
                  'version', 'metadata', 'subjects']


class DandisetListSerializer(serializers.ModelSerializer):
    """
    Serializes a dandiset with only metadata (no subjects/files)
    """
    class Meta:
        model = Dandiset
        fields = ['created', 'updated', 'dandi_id',
                  'version', 'metadata']


class DandisetPublishSerializer(serializers.Serializer):
    girder_id = serializers.CharField()
    token = serializers.CharField(allow_blank=True, default='')
