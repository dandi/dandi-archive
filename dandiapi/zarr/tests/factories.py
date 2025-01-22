from __future__ import annotations

import factory

from dandiapi.api.tests.factories import DandisetFactory
from dandiapi.zarr.models import ZarrArchive


class ZarrArchiveFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ZarrArchive

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
    embargoed = True
