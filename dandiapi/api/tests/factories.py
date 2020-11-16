from django.contrib.auth.models import User
import factory

from dandiapi.api.models import (
    Asset,
    AssetBlob,
    AssetMetadata,
    Dandiset,
    Validation,
    Version,
    VersionMetadata,
)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.SelfAttribute('email')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class DandisetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Dandiset

    # draft_folder_id = factory.Faker('hexify', text='^' * 24)

    # Pass in 'dandiset' to link the generated DraftVersionFactory to our just-generated
    # DandisetFactory. This will call DraftVersionFactory(dandiset=our_new_dandiset), thus skipping
    # the SubFactory.
    # draft_version = factory.RelatedFactory(
    #    'dandiapi.api.tests.factories.DraftVersionFactory', factory_related_name='dandiset'
    # )


class VersionMetadataFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = VersionMetadata

    metadata = factory.Faker('pydict', value_types=['str', 'float', 'int'])
    name = factory.Faker('sentence')


class BaseVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    dandiset = factory.SubFactory(DandisetFactory)
    metadata = factory.SubFactory(VersionMetadataFactory)


# class VersionFactory(BaseVersionFactory):
#     class Meta:
#         model = Version

#     dandiset = factory.SubFactory(DandisetFactory)


class DraftVersionFactory(BaseVersionFactory):
    class Meta:
        model = Version

    version = 'draft'


class PublishedVersionFactory(BaseVersionFactory):
    class Meta:
        model = Version


class AssetBlobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetBlob

    blob = factory.django.FileField(data=b'somefilebytes')
    path = factory.Faker('file_path', extension='nwb')
    # TODO: This sha256 is technically invalid for the blob
    sha256 = factory.Faker('sha256')


class AssetMetadataFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetMetadata

    metadata = factory.Faker('pydict', value_types=['str', 'float', 'int'])


class AssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Asset

    version = factory.SubFactory(DraftVersionFactory)
    metadata = factory.SubFactory(AssetMetadataFactory)
    blob = factory.SubFactory(AssetBlobFactory)


class ValidationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Validation

    blob = factory.django.FileField(data=b'validationbytes')
    # TODO: This sha256 is technically invalid for the blob
    sha256 = factory.Faker('sha256')
    state = 'SUCCEEDED'
    error = factory.Faker('sentence')
