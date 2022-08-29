import hashlib

from django.core import files as django_files
import factory
import faker

from dandiapi.api.tests.factories import DandisetFactory
from dandiapi.zarr.models import ZarrArchive, ZarrUploadFile


class ZarrArchiveFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ZarrArchive

    zarr_id = factory.Faker('uuid4')
    name = factory.Faker('catch_phrase')
    dandiset = factory.SubFactory(DandisetFactory)


class ZarrUploadFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ZarrUploadFile

    zarr_archive = factory.SubFactory(ZarrArchiveFactory)

    @factory.lazy_attribute
    def path(self):
        # No / prefix
        return faker.Faker().file_path(extension='nwb')[1:]

    @factory.lazy_attribute
    def blob(self):
        return django_files.File(
            django_files.base.ContentFile(faker.Faker().binary(length=100)).file,
            self.zarr_archive.s3_path(self.path),
        )

    @factory.lazy_attribute
    def etag(self):
        h = hashlib.md5()
        h.update(self.blob.read())
        self.blob.seek(0)
        return h.hexdigest()
