from __future__ import annotations

from django.db.models.query import QuerySet
from django.db.models.query_utils import Q
from django.http.response import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from dandiapi.api.models.asset import Asset
from dandiapi.api.views.serializers import AssetSerializer
from dandiapi.search.models import AssetSearch


class SearchQuerySerializer(serializers.Serializer):
    file_type = serializers.MultipleChoiceField(
        choices=[
            ('application/x-nwb', 'nwb'),
            ('image/', 'image'),
            ('text/', 'text'),
            ('video/', 'video'),
        ],
        required=False,
    )
    # TODO: assert that file_size_max > file_size_min
    file_size_min = serializers.IntegerField(min_value=0, required=False)
    file_size_max = serializers.IntegerField(min_value=0, required=False)
    measurement_technique = serializers.MultipleChoiceField(
        choices=[
            ('signal filtering technique', 'signal filtering technique'),
            ('spike sorting technique', 'spike sorting technique'),
            (
                'multi electrode extracellular electrophysiology recording technique',
                'multi electrode extracellular electrophysiology recording technique',
            ),
            ('voltage clamp technique', 'voltage clamp technique'),
            ('surgical technique', 'surgical technique'),
            ('behavioral technique', 'behavioral technique'),
            ('current clamp technique', 'current clamp technique'),
            ('fourier analysis technique', 'fourier analysis technique'),
            ('two-photon microscopy technique', 'two-photon microscopy technique'),
            ('patch clamp technique', 'patch clamp technique'),
            ('analytical technique', 'analytical technique'),
        ],
        required=False,
    )
    genotype = serializers.ListField(child=serializers.CharField(), required=False)
    species = serializers.MultipleChoiceField(
        choices=[
            ('Rattus norvegicus - Norway rat', 'Rattus norvegicus - Norway rat'),
            ('Danio rerio - Zebra fish', 'Danio rerio - Zebra fish'),
            ('Macaca nemestrina - Pig-tailed macaque', 'Macaca nemestrina - Pig-tailed macaque'),
            ('Danio rerio - Leopard danio', 'Danio rerio - Leopard danio'),
            ('Mus musculus - House mouse', 'Mus musculus - House mouse'),
            ('Cricetulus griseus - Cricetulus aureus', 'Cricetulus griseus - Cricetulus aureus'),
            ('Drosophila melanogaster - Fruit fly', 'Drosophila melanogaster - Fruit fly'),
            ('Human', 'Human'),
            ('Common fruit fly', 'Common fruit fly'),
            ('Rhesus monkey', 'Rhesus monkey'),
            ('Drosophila suzukii', 'Drosophila suzukii'),
            ('Rat; norway rat; rats; brown rat', 'Rat; norway rat; rats; brown rat'),
            ('Homo sapiens - Human', 'Homo sapiens - Human'),
            ('House mouse', 'House mouse'),
            ('Brown rat', 'Brown rat'),
            ('Macaca mulatta - Rhesus monkey', 'Macaca mulatta - Rhesus monkey'),
        ],
        required=False,
    )

    def to_queryset(self, qs: QuerySet[AssetSearch] | None = None) -> QuerySet[AssetSearch]:
        qs = qs if qs is not None else AssetSearch._default_manager.all()

        file_type_filter = Q()
        for file_type in self.validated_data.get('file_type', []):
            file_type_filter |= Q(asset_metadata__encodingFormat__istartswith=file_type)
        qs = qs.filter(file_type_filter)

        genotype_filter = Q()
        for genotype in self.validated_data.get('genotype', []):
            genotype_filter |= Q(asset_metadata__wasAttributedTo__0__genotype__name=genotype)
        qs = qs.filter(genotype_filter)

        species_filter = Q()
        for species in self.validated_data.get('species', []):
            species_filter |= Q(asset_metadata__wasAttributedTo__0__species__name=species)
        qs = qs.filter(species_filter)

        measurement_technique_filter = Q()
        for measurement_technique in self.validated_data.get('measurement_technique', []):
            measurement_technique_filter |= Q(
                asset_metadata__measurementTechnique__contains=[{'name': measurement_technique}]
            )
        qs = qs.filter(measurement_technique_filter)

        if self.validated_data.get('file_size_max'):
            qs = qs.filter(asset_size__lte=self.validated_data['file_size_max'])

        if self.validated_data.get('file_size_min'):
            qs = qs.filter(asset_size__gte=self.validated_data['file_size_min'])

        return qs


@swagger_auto_schema(methods=['GET'], auto_schema=None)
@api_view(['GET'])
@permission_classes([AllowAny])
def search_assets(request):
    serializer = SearchQuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)

    # TODO: filter by permissions (embargo/dandiset owner)
    return JsonResponse(
        AssetSerializer(
            Asset.objects.select_related('blob').filter(id__in=serializer.to_queryset())[:100],
            many=True,
        ).data,
        safe=False,
    )
