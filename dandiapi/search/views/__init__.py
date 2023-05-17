from django.db.models.query import QuerySet
from django.http.response import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from dandiapi.search.models import AssetSearch


class GenotypeSearchSerializer(serializers.Serializer):
    genotype = serializers.CharField(required=False)

    def to_queryset(self, qs: QuerySet[AssetSearch] | None = None) -> QuerySet[AssetSearch]:
        qs = qs if qs is not None else AssetSearch._default_manager.all()

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

    # TODO: filter by permissions (embargo/dandiset owner)
    return JsonResponse(list(serializer.to_queryset()), safe=False)


class SpeciesSearchSerializer(serializers.Serializer):
    species = serializers.CharField(required=False)

    def to_queryset(self, qs: QuerySet[AssetSearch] | None = None) -> QuerySet[AssetSearch]:
        qs = qs if qs is not None else AssetSearch._default_manager.all()

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

    # TODO: filter by permissions (embargo/dandiset owner)
    return JsonResponse(list(serializer.to_queryset()), safe=False)
