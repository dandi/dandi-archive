from __future__ import annotations

from typing import TYPE_CHECKING

from django.http.response import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from dandiapi.search.models import AssetSearch

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.db.models.query import QuerySet


class SearchSerializer(serializers.Serializer):
    def to_queryset(self, user: User) -> QuerySet[AssetSearch]:
        return AssetSearch.objects.visible_to(user)


class GenotypeSearchSerializer(SearchSerializer):
    genotype = serializers.CharField(required=False)

    def to_queryset(self, user: User) -> QuerySet[AssetSearch]:
        qs = super().to_queryset(user)

        genotype: str | None = self.validated_data.get('genotype')
        if genotype:
            # TODO: take advantage of trigram index?
            qs = qs.filter(asset_metadata__wasAttributedTo__0__genotype__icontains=genotype)

        # Filter out empty string genotype
        qs = qs.exclude(asset_metadata__wasAttributedTo__0__genotype__exact='')

        return qs.values_list('asset_metadata__wasAttributedTo__0__genotype', flat=True).distinct()[
            :10
        ]


@swagger_auto_schema(methods=['GET'], auto_schema=None)
@api_view(['GET'])
@permission_classes([AllowAny])
def search_genotypes(request):
    serializer = GenotypeSearchSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)

    return JsonResponse(list(serializer.to_queryset(user=request.user)), safe=False)


class SpeciesSearchSerializer(SearchSerializer):
    species = serializers.CharField(required=False)

    def to_queryset(self, user: User) -> QuerySet[AssetSearch]:
        qs = super().to_queryset(user)

        species: str | None = self.validated_data.get('species')
        if species:
            # TODO: take advantage of trigram index?
            qs = qs.filter(asset_metadata__wasAttributedTo__0__genotype__icontains=species)

        # Filter out empty string species
        qs = qs.exclude(asset_metadata__wasAttributedTo__0__species__name__exact='')

        return qs.values_list(
            'asset_metadata__wasAttributedTo__0__species__name', flat=True
        ).distinct()[:10]


@swagger_auto_schema(methods=['GET'], auto_schema=None)
@api_view(['GET'])
@permission_classes([AllowAny])
def search_species(request):
    serializer = SpeciesSearchSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)

    return JsonResponse(list(serializer.to_queryset(user=request.user)), safe=False)
