from collections import OrderedDict
from typing import Any

from django.conf import settings
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models.query_utils import Q
from rest_framework import serializers

from dandiapi.api.models import Asset, AssetBlob, AssetPath, Dandiset, Version
from dandiapi.search.models import AssetSearch


def extract_contact_person(version):
    """Extract a version's contact person from its metadata."""
    # TODO: move this logic into dandischema since it is schema-dependant
    contributors = version.metadata.get('contributor')
    if contributors is not None:
        for contributor in contributors:
            name = contributor.get('name')
            role_names = contributor.get('roleName')
            if name is not None and role_names is not None and 'dcite:ContactPerson' in role_names:
                return name
    return ''


# The default ModelSerializer for User fails if the user already exists
class UserSerializer(serializers.Serializer):
    username = serializers.CharField(validators=[UnicodeUsernameValidator()])


class UserDetailSerializer(serializers.Serializer):
    username = serializers.CharField(validators=[UnicodeUsernameValidator()])
    name = serializers.CharField(validators=[UnicodeUsernameValidator()])
    admin = serializers.BooleanField()
    status = serializers.CharField()


class DandisetSerializer(serializers.ModelSerializer):
    contact_person = serializers.SerializerMethodField(method_name='get_contact_person')

    class Meta:
        model = Dandiset
        fields = [
            'identifier',
            'created',
            'modified',
            'contact_person',
            'embargo_status',
        ]
        read_only_fields = ['created']

    def get_contact_person(self, dandiset: Dandiset):
        latest_version = dandiset.versions.order_by('-created').first()

        if latest_version is None:
            return ''

        return extract_contact_person(latest_version)


class CreateDandisetQueryParameterSerializer(serializers.Serializer):
    embargo = serializers.BooleanField(required=False, default=False)


class VersionMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
        fields = ['metadata', 'name']
        # By default, validators contains a single UniqueTogether constraint.
        # This will fail serialization if the version metadata already exists,
        # which we do not want.
        validators = []

    def validate(self, data):
        data['metadata'].setdefault('schemaVersion', settings.DANDI_SCHEMA_VERSION)
        return super().validate(data)


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


class DandisetVersionSerializer(serializers.ModelSerializer):
    """The version serializer nested within the Dandiset Serializer."""

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
        ]
        read_only_fields = ['created']

    # Override the model methods with fields populated from a query
    asset_count = serializers.IntegerField(source='num_assets')
    size = serializers.IntegerField(source='total_size')


class DandisetListSerializer(DandisetSerializer):
    """The dandiset serializer to be used in the listing endpoint."""

    class Meta(DandisetSerializer.Meta):
        fields = DandisetSerializer.Meta.fields + ['most_recent_published_version', 'draft_version']

    def get_draft_version(self, dandiset):
        draft = self.context['dandisets'].get(dandiset.id, {}).get('draft')
        if draft is None:
            return None

        return DandisetVersionSerializer(draft).data

    def get_most_recent_published_version(self, dandiset):
        version = self.context['dandisets'].get(dandiset.id, {}).get('published')
        if version is None:
            return None

        return DandisetVersionSerializer(version).data

    def get_contact_person(self, dandiset):
        draft = self.context['dandisets'].get(dandiset.id, {}).get('draft')
        published = self.context['dandisets'].get(dandiset.id, {}).get('published')

        contact = ''
        if published is not None:
            contact = extract_contact_person(published)
        elif draft is not None:
            contact = extract_contact_person(draft)

        return contact

    most_recent_published_version = serializers.SerializerMethodField()
    draft_version = serializers.SerializerMethodField()


class DandisetSearchResultListSerializer(DandisetListSerializer):
    asset_counts = serializers.SerializerMethodField(method_name='get_asset_counts')

    class Meta(DandisetListSerializer.Meta):
        fields = DandisetListSerializer.Meta.fields + ['asset_counts']

    def get_asset_counts(self, dandiset):
        return self.context['asset_counts'].get(dandiset.id, {})


class DandisetDetailSerializer(DandisetSerializer):
    class Meta(DandisetSerializer.Meta):
        fields = DandisetSerializer.Meta.fields + ['most_recent_published_version', 'draft_version']

    most_recent_published_version = VersionSerializer(read_only=True)
    draft_version = VersionSerializer(read_only=True)


class DandisetQueryParameterSerializer(serializers.Serializer):
    draft = serializers.BooleanField(default=True)
    empty = serializers.BooleanField(default=True)
    embargoed = serializers.BooleanField(default=True)
    user = serializers.CharField(required=False)


class DandisetSearchQueryParameterSerializer(DandisetQueryParameterSerializer):
    file_type = serializers.MultipleChoiceField(
        choices=[
            ('application/x-nwb', 'nwb'),
            ('image/', 'image'),
            ('text/', 'text'),
            ('video/', 'video'),
        ],
        required=False,
    )
    file_size_min = serializers.IntegerField(min_value=0, required=False)
    file_size_max = serializers.IntegerField(min_value=0, required=False)
    measurement_technique = serializers.MultipleChoiceField(
        choices=[
            ('signal filtering technique', 'signal filtering technique'),
            ('spike sorting technique', 'spike sorting technique'),
            (
                'multi electrode extracellular electrophysiology recording technique',
                'multi electrode extracellular electrophysiology recording technique',
            ),
            ('voltage clamp technique', 'voltage clamp technique'),
            ('surgical technique', 'surgical technique'),
            ('behavioral technique', 'behavioral technique'),
            ('current clamp technique', 'current clamp technique'),
            ('fourier analysis technique', 'fourier analysis technique'),
            ('two-photon microscopy technique', 'two-photon microscopy technique'),
            ('patch clamp technique', 'patch clamp technique'),
            ('analytical technique', 'analytical technique'),
        ],
        required=False,
    )
    genotype = serializers.ListField(child=serializers.CharField(), required=False)
    species = serializers.MultipleChoiceField(choices=[], required=False)

    def __init__(self, instance=None, data=..., **kwargs) -> None:
        super().__init__(instance, data, **kwargs)
        # The queryset can't be evaluated at compile time, so we evaluate it here
        # in the __init__ method
        self.fields['species'].choices = list(
            AssetSearch.objects.values_list(
                'asset_metadata__wasAttributedTo__0__species__name', flat=True
            ).distinct()
        )

    def validate(self, data: OrderedDict[str, Any]) -> OrderedDict[str, Any]:
        if (
            'file_size_max' in data
            and 'file_size_min' in data
            and data['file_size_max'] < data['file_size_min']
        ):
            raise serializers.ValidationError('file_size_max must be greater than file_size_min')
        return data

    def to_query_filters(self):
        # create a set of Q object filters for the AssetSearch model
        query_filters = {
            'file_type': Q(),
            'file_size': Q(),
            'genotype': Q(),
            'species': Q(),
            'measurement_technique': Q(),
        }

        for file_type in self.validated_data.get('file_type', []):
            query_filters['file_type'] |= Q(asset_metadata__encodingFormat__istartswith=file_type)

        if self.validated_data.get('file_size_max'):
            query_filters['file_size'] &= Q(asset_size__lte=self.validated_data['file_size_max'])
        if self.validated_data.get('file_size_min'):
            query_filters['file_size'] &= Q(asset_size__gte=self.validated_data['file_size_min'])

        for genotype in self.validated_data.get('genotype', []):
            query_filters['genotype'] |= Q(asset_metadata__wasAttributedTo__0__genotype=genotype)

        for species in self.validated_data.get('species', []):
            query_filters['species'] |= Q(asset_metadata__wasAttributedTo__0__species__name=species)

        for measurement_technique in self.validated_data.get('measurement_technique', []):
            query_filters['measurement_technique'] |= Q(
                asset_metadata__measurementTechnique__contains=[{'name': measurement_technique}]
            )

        return query_filters


class VersionDetailSerializer(VersionSerializer):
    contact_person = serializers.SerializerMethodField(method_name='get_contact_person')

    class Meta(VersionSerializer.Meta):
        fields = VersionSerializer.Meta.fields + [
            'asset_validation_errors',
            'version_validation_errors',
            'metadata',
            'contact_person',
        ]

    # rename this field in the serializer to differentiate from asset_validation_errors
    version_validation_errors = serializers.JSONField(source='validation_errors')

    def get_contact_person(self, obj):
        return extract_contact_person(obj)


class AssetBlobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetBlob
        fields = [
            'blob_id',
            'etag',
            'sha256',
            'size',
        ]


class AssetValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['status', 'validation_errors']


class AssetDownloadQueryParameterSerializer(serializers.Serializer):
    content_disposition = serializers.ChoiceField(['attachment', 'inline'], default='attachment')


class EmbargoedSlugRelatedField(serializers.SlugRelatedField):
    """
    A Field for cleanly serializing embargoed model fields.

    Embargoed fields are paired with their non-embargoed equivalents, like "blob" and
    "embargoed_blob", or "zarr" and "embargoed_zarr". There are DB constraints in place to ensure
    that only one field is defined at a time. When serializing one of those pairs, we would like to
    conceal the fact that the field might be embargoed by silently using the embargoed model field
    in place of the normal field if it is defined.
    """

    def get_attribute(self, instance: Asset):
        attr = super().get_attribute(instance)
        if attr is None:
            # The normal field was not defined on the model, try the embargoed_ variant instead
            embargoed_source = f'embargoed_{self.source}'
            attr = getattr(instance, embargoed_source, None)
        return attr


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            'asset_id',
            'blob',
            'zarr',
            'path',
            'size',
            'created',
            'modified',
            'metadata',
        ]
        read_only_fields = ['created']

    blob = EmbargoedSlugRelatedField(slug_field='blob_id', read_only=True)
    zarr = serializers.SlugRelatedField(slug_field='zarr_id', read_only=True)

    def __init__(self, *args, metadata=True, **kwargs):
        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        # Don't include metadata unless specified
        if not metadata:
            self.fields.pop('metadata')


class AssetDetailSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        fields = AssetSerializer.Meta.fields + ['metadata']


class AssetListSerializer(serializers.Serializer):
    glob = serializers.CharField(required=False)
    metadata = serializers.BooleanField(required=False, default=False)


class AssetPathsQueryParameterSerializer(serializers.Serializer):
    path_prefix = serializers.CharField(default='')


class AssetFileSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        fields = ['asset_id', 'url']

    url = serializers.URLField(source='s3_url')


class AssetPathsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetPath
        fields = [
            'path',
            'version',
            'aggregate_files',
            'aggregate_size',
            'asset',
        ]
        read_only_fields = ['created']

    asset = AssetFileSerializer()
