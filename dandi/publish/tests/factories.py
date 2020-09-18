from django.contrib.auth.models import User
import factory.django

from dandi.publish.models import Asset, Dandiset, DraftVersion, Version


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker('user_name')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class DandisetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Dandiset

    draft_folder_id = factory.Faker('hexify', text='^' * 24)

    # Pass in 'dandiset' to link the generated DraftVersionFactory to our just-generated
    # DandisetFactory. This will call DraftVersionFactory(dandiset=our_new_dandiset), thus skipping
    # the SubFactory.
    draft_version = factory.RelatedFactory(
        'dandi.publish.tests.factories.DraftVersionFactory', factory_related_name='dandiset'
    )


class BaseVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    name = factory.Faker('sentence')

    metadata = factory.Faker('pydict', value_types=['str', 'float', 'int'])


class VersionFactory(BaseVersionFactory):
    class Meta:
        model = Version

    dandiset = factory.SubFactory(DandisetFactory)


class DraftVersionFactory(BaseVersionFactory):
    class Meta:
        model = DraftVersion

    # Pass in draft_version=None to prevent DandisetFactory from creating another DraftVersion
    # (this disables the RelatedFactory).
    dandiset = factory.SubFactory(DandisetFactory, draft_version=None)


class AssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Asset

    version = factory.SubFactory(VersionFactory)
    path = factory.Faker('file_path', extension='nwb')
    # size = factory.LazyAttribute(lambda asset: asset.blob.size)
    size = factory.SelfAttribute('blob.size')
    # TODO: This sha256 is technically invalid for the blob
    sha256 = factory.Faker('hexify', text='^' * 64)
    metadata = factory.Faker('pydict', value_types=['str', 'float', 'int'])
    blob = factory.django.FileField(data=b'somefilebytes')
