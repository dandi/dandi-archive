from __future__ import annotations

import hashlib
from typing import Any

from django.core.files.base import ContentFile
import factory
from zarr_checksum.generators import ZarrArchiveFile

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.tests.factories import DandisetFactory
from dandiapi.zarr.models import ZarrArchive

from .utils import PostgenerationAttributesFactory


class ZarrArchiveFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ZarrArchive
        skip_postgeneration_save = True

    zarr_id = factory.Faker('uuid4')
    name = factory.Faker('catch_phrase')
    dandiset = factory.SubFactory(DandisetFactory)

    @factory.post_generation
    def ensure_draft_version(obj: ZarrArchive, *args, **kwargs):  # type: ignore  # noqa: N805, PGH003
        from dandiapi.api.tests.factories import DraftVersionFactory

        if obj.dandiset.versions.filter(version='draft').exists():
            return

        DraftVersionFactory(dandiset=obj.dandiset)


class EmbargoedZarrArchiveFactory(ZarrArchiveFactory):
    dandiset = factory.SubFactory(DandisetFactory, embargo_status=Dandiset.EmbargoStatus.EMBARGOED)


class ZarrFileFactory(PostgenerationAttributesFactory):
    class Meta:
        model = ZarrArchiveFile

    class Params:
        blob = factory.Faker('binary', length=100)
        zarr_archive = factory.SubFactory(ZarrArchiveFactory)

    path = factory.Faker('numerify', text='#/#/@#/@#/@#/@#')
    size = factory.LazyAttribute(lambda self: len(self.blob))
    digest = factory.LazyAttribute(lambda self: hashlib.md5(self.blob).hexdigest())

    @classmethod
    def _after_postgeneration(
        cls,
        obj: ZarrArchiveFile,
        create: bool,  # noqa: FBT001
        results=None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        super()._after_postgeneration(obj, create, results)
        if not create:
            return

        blob: bytes = attributes['blob']
        zarr_archive: ZarrArchive = attributes['zarr_archive']
        zarr_archive.storage.save(
            name=zarr_archive.s3_path(str(obj.path)), content=ContentFile(blob)
        )
