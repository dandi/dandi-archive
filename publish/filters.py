from django_filters import rest_framework as filters

from .models import Asset


class AssetFilter(filters.FilterSet):
    path_prefix = filters.CharFilter(lookup_expr='startswith', field_name='path')

    class Meta:
        model = Asset
        fields = ['path_prefix']
