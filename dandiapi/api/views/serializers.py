from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers

from dandiapi.api.models import Asset, AssetBlob, Dandiset, Version


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
    embargo = serializers.BooleanField(required=False)


class VersionMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
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
            'status',
            'created',
            'modified',
            'dandiset',
        ]
        read_only_fields = ['created']

    dandiset = DandisetSerializer()
    # name = serializers.SlugRelatedField(read_only=True, slug_field='name')


class DandisetDetailSerializer(DandisetSerializer):
    class Meta(DandisetSerializer.Meta):
        fields = DandisetSerializer.Meta.fields + ['most_recent_published_version', 'draft_version']

    most_recent_published_version = VersionSerializer(read_only=True)
    draft_version = VersionSerializer(read_only=True)


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
        ]
        read_only_fields = ['created']

    blob = EmbargoedSlugRelatedField(slug_field='blob_id', read_only=True)
    zarr = serializers.SlugRelatedField(slug_field='zarr_id', read_only=True)


class AssetDetailSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        fields = AssetSerializer.Meta.fields + ['metadata']


class AssetFolderSerializer(serializers.Serializer):
    size = serializers.IntegerField()
    num_files = serializers.IntegerField()
    created = serializers.DateTimeField()
    modified = serializers.DateTimeField()


class AssetPathsSerializer(serializers.Serializer):
    folders = serializers.DictField(child=AssetFolderSerializer())
    files = serializers.DictField(child=AssetSerializer())
