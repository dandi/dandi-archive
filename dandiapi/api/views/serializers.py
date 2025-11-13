from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from dandischema.consts import DANDI_SCHEMA_VERSION
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models.query_utils import Q
from django.utils import timezone
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.validators import ValidationError

from dandiapi.api.models import Asset, AssetBlob, AssetPath, Dandiset, Upload, Version
from dandiapi.search.models import AssetSearch

if TYPE_CHECKING:
    from collections import OrderedDict


def extract_contact_person(version: Version) -> str:
    """Extract a version's contact person from its metadata."""
    # TODO: move this logic into dandischema since it is schema-dependant
    contributors = version.metadata.get('contributor')
    if contributors is not None and isinstance(contributors, list):
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
    star_count = serializers.SerializerMethodField()
    is_starred = serializers.SerializerMethodField()

    class Meta:
        model = Dandiset
        fields = [
            'identifier',
            'created',
            'modified',
            'contact_person',
            'embargo_status',
            'star_count',
            'is_starred',
        ]
        read_only_fields = ['created']

    def get_contact_person(self, dandiset: Dandiset):
        latest_version = dandiset.versions.order_by('-created').first()

        if latest_version is None:
            return ''

        return extract_contact_person(latest_version)

    def get_star_count(self, dandiset):
        return dandiset.star_count

    def get_is_starred(self, dandiset):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return dandiset.is_starred_by(request.user)


class CreateDandisetQueryParameterSerializer(serializers.Serializer):
    embargo = serializers.BooleanField(required=False, default=False)
    funding_source = serializers.CharField(required=False, allow_blank=True)
    award_number = serializers.CharField(required=False, allow_blank=True)
    embargo_end_date = serializers.DateField(
        default=lambda: timezone.now().date() + timedelta(days=365 * 2)
    )

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate the embargo end date.

        The semantics for this are as follows:

        - User supplies no funding source and no award number
            => Successful, embargo end date set to two years in the future
               (automatic/not changeable by user)

        - User supplies a funding source but no award number
            => Result: Failure, supplying a funding source with no award number is not valid

        - User supplies an award number but no funding source
            => Result: Failure, supplying a funding source with no award number is not valid

        - User supplies both a funding source and an award number
            => Result: Successful, embargo end date is set to whatever the user specified in
               form (defaults to two years, but user can specify up to a maximum of 5 years)
        """
        embargo: bool = data['embargo']
        funding_source: str | None = data.get('funding_source')
        award_number: str | None = data.get('award_number')
        embargo_end_date: date = data['embargo_end_date']

        # If embargo is not set, we don't need to validate the embargo end date
        if not embargo:
            return data

        # Supplying one of funding source or award number mandates supplying the other
        if funding_source is not None and award_number is None:
            raise ValidationError('Award number is required when funding source is set')
        if funding_source is None and award_number is not None:
            raise ValidationError('Funding source is required when award number is set')

        # If the dandiset has no funding source, the embargo end date must be within 2 years.
        # Otherwise, it must be within 5 years.
        if funding_source is None:
            max_end_date = timezone.now().date() + timedelta(days=365 * 2)
        else:
            max_end_date = timezone.now().date() + timedelta(days=365 * 5)

        if embargo_end_date > max_end_date:
            raise ValidationError('Invalid embargo end date')

        return data


class VersionMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
        fields = ['metadata', 'name']
        # By default, validators contains a single UniqueTogether constraint.
        # This will fail serialization if the version metadata already exists,
        # which we do not want.
        validators = []

    def validate(self, data):
        data['metadata'].setdefault('schemaVersion', DANDI_SCHEMA_VERSION)
        return super().validate(data)


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
        fields = [
            'version',
            'name',
            'asset_count',
            'active_uploads',
            'size',
            'status',
            'created',
            'modified',
            'dandiset',
        ]
        read_only_fields = ['created']

    dandiset = DandisetSerializer()
    # name = serializers.SlugRelatedField(read_only=True, slug_field='name')

    def __init__(self, *args, child_context=False, **kwargs):
        if child_context:
            del self.fields['dandiset']

        super().__init__(*args, **kwargs)


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
        fields = [*DandisetSerializer.Meta.fields, 'most_recent_published_version', 'draft_version']

    @swagger_serializer_method(serializer_or_field=DandisetVersionSerializer)
    def get_draft_version(self, dandiset):
        draft = self.context['dandisets'].get(dandiset.id, {}).get('draft')
        if draft is None:
            return None

        return DandisetVersionSerializer(draft).data

    @swagger_serializer_method(serializer_or_field=DandisetVersionSerializer)
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

    def get_star_count(self, dandiset):
        return self.context['stars'][dandiset.id]['total']

    def get_is_starred(self, dandiset):
        return self.context['stars'][dandiset.id]['starred_by_current_user']

    most_recent_published_version = serializers.SerializerMethodField()
    draft_version = serializers.SerializerMethodField()


class DandisetSearchResultListSerializer(DandisetListSerializer):
    asset_counts = serializers.SerializerMethodField(method_name='get_asset_counts')

    class Meta(DandisetListSerializer.Meta):
        fields = [*DandisetListSerializer.Meta.fields, 'asset_counts']

    def get_asset_counts(self, dandiset):
        return self.context['asset_counts'].get(dandiset.id, {})


class DandisetDetailSerializer(DandisetSerializer):
    class Meta(DandisetSerializer.Meta):
        fields = [*DandisetSerializer.Meta.fields, 'most_recent_published_version', 'draft_version']

    most_recent_published_version = VersionSerializer(read_only=True, child_context=True)
    draft_version = VersionSerializer(read_only=True, child_context=True)


class DandisetQueryParameterSerializer(serializers.Serializer):
    draft = serializers.BooleanField(
        default=True,
        help_text='Whether to include dandisets that only have draft '
        "versions (i.e., haven't been published yet).",
    )
    empty = serializers.BooleanField(default=True, help_text='Whether to include empty dandisets.')
    embargoed = serializers.BooleanField(
        default=False, help_text='Whether to include embargoed dandisets.'
    )
    user = serializers.ChoiceField(
        choices=['me'],
        required=False,
        help_text='Set this value to "me" to only return dandisets owned by the current user.',
    )
    starred = serializers.BooleanField(
        default=False,
        help_text='Whether to filter the result to only dandisets'
        ' that have been starred by the current user.',
    )
    search = serializers.CharField(
        required=False,
        help_text='Search terms to filter the results.',
    )


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
            AssetSearch.objects.exclude(species='').values_list('species', flat=True).distinct()
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
            query_filters['species'] |= Q(species=species)

        for measurement_technique in self.validated_data.get('measurement_technique', []):
            query_filters['measurement_technique'] |= Q(
                asset_metadata__measurementTechnique__contains=[{'name': measurement_technique}]
            )

        return query_filters


class VersionDetailSerializer(VersionSerializer):
    contact_person = serializers.SerializerMethodField(method_name='get_contact_person')

    class Meta(VersionSerializer.Meta):
        fields = [
            *VersionSerializer.Meta.fields,
            'asset_validation_errors',
            'version_validation_errors',
            'metadata',
            'contact_person',
        ]

    # rename this field in the serializer to differentiate from asset_validation_errors
    version_validation_errors = serializers.JSONField(source='validation_errors')

    def get_contact_person(self, obj):
        return extract_contact_person(obj)


class DandisetUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upload
        exclude = [
            'dandiset',
            'embargoed',
            'id',
            'multipart_upload_id',
        ]


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

    blob = serializers.SlugRelatedField(slug_field='blob_id', read_only=True)
    zarr = serializers.SlugRelatedField(slug_field='zarr_id', read_only=True)
    metadata = serializers.JSONField(source='full_metadata')

    def __init__(self, *args, metadata=True, **kwargs):
        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        # Don't include metadata unless specified
        if not metadata:
            self.fields.pop('metadata')


class AssetDetailSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        fields = [*AssetSerializer.Meta.fields, 'metadata']


class AssetListSerializer(serializers.Serializer):
    glob = serializers.CharField(required=False)
    metadata = serializers.BooleanField(required=False, default=False)
    zarr = serializers.BooleanField(required=False, default=False)


class AssetPathsQueryParameterSerializer(serializers.Serializer):
    path_prefix = serializers.CharField(default='')


class PaginationQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(default=1)
    page_size = serializers.IntegerField(default=100)


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
