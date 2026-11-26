from __future__ import annotations

from typing import TYPE_CHECKING

from django.http.response import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
import sentry_sdk

from dandiapi.api.services.search.values import SUMMARY_OPERATORS, summary_operator_values
from dandiapi.api.views.common import DandiPagination
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

        return (
            qs.order_by('asset_metadata__wasAttributedTo__0__genotype')
            .values_list('asset_metadata__wasAttributedTo__0__genotype', flat=True)
            .distinct()[:10]
        )


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
            qs = qs.filter(species__icontains=species)

        # Filter out empty string species
        qs = qs.exclude(species__exact='')

        return qs.order_by('species').values_list('species', flat=True).distinct()


@swagger_auto_schema(methods=['GET'], auto_schema=None)
@api_view(['GET'])
@permission_classes([AllowAny])
def search_species(request):
    serializer = SpeciesSearchSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)

    qs = serializer.to_queryset(user=request.user)

    paginator = DandiPagination()
    qs = paginator.paginate_queryset(qs, request)

    response = paginator.get_paginated_response(qs)

    if response.get('next') is not None:
        sentry_sdk.capture_message(
            'Species search pagination is not implemented on frontend',
            level='warning',
        )

    return response


@swagger_auto_schema(methods=['GET'], auto_schema=None)
@api_view(['GET'])
@permission_classes([AllowAny])
def search_operator_values(request):
    """List the values of a search operator such as ``species:``, for autocompletion.

    Takes ``?operator=species`` (or approach, technique, standard, variable) and
    returns ``[{"value": ..., "dandisets": n}, ...]``, most common first.
    """
    operator = request.query_params.get('operator', '')
    if operator not in SUMMARY_OPERATORS:
        return JsonResponse(
            {'detail': f'operator must be one of: {", ".join(sorted(SUMMARY_OPERATORS))}'},
            status=400,
        )
    response = JsonResponse(summary_operator_values(operator), safe=False)
    # The same for every user (only open dandisets are counted), and only
    # changes as assets are added, so browsers may reuse it for a while.
    response['Cache-Control'] = 'public, max-age=600'
    return response
