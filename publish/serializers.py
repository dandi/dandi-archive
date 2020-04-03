from rest_framework import serializers

from .models import Dandiset, NWBFile, Subject


class DandisetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dandiset


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject


class NWBFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = NWBFile
