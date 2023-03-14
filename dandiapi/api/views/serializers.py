from django.conf import settings
from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from dandiapi.api.models import Asset, AssetBlob, AssetPath, Dandiset, Version


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


class VersionDetailSerializer(VersionSerializer):
    contact_person = serializers.SerializerMethodField(method_name='get_contact_person')

    class Meta(VersionSerializer.Meta):
        fields = VersionSerializer.Meta.fields + [
            'asset_validation_errors',
            'version_validation_errors',
            'metadata',
            'contact_person',
        ]

    status = serializers.CharField(source='publish_status')

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
    content_disposition = serializers.CharField(default='attachment')

    def validate(self, data):
        value = data['content_disposition']

        if value not in ['attachment', 'inline']:
            raise ValidationError(
                f'Illegal value {value} for parameter "content_disposition"', code=400
            )

        return super().validate(data)


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
