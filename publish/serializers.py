from rest_framework import serializers

from .models import Dandiset, NWBFile, Subject


class DandisetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dandiset
        fields = '__all__'


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'


class NWBFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = NWBFile
        fields = '__all__'


class DandisetPublishSerializer(serializers.Serializer):
    girder_id = serializers.CharField()
    token = serializers.CharField(allow_blank=True, default='')
