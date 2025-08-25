from __future__ import annotations

from typing import TYPE_CHECKING

from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import CursorPagination

from dandiapi.api.models import AuditRecord
from dandiapi.api.permissions import IsApproved

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.response import Response


class AssetAuditEventQuerySerializer(serializers.Serializer):
    before = serializers.DateTimeField(allow_null=True, default=None)
    after = serializers.DateTimeField(allow_null=True, default=None)
    reverse_order = serializers.BooleanField(default=False)


class AssetAuditEventResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditRecord
        fields = [
            'id',
            'dandiset_id',
            'timestamp',
            'record_type',
            'details',
        ]

    details = serializers.SerializerMethodField()

    # Don't need to return metadata
    def get_details(self, obj: AuditRecord):
        obj.details.pop('metadata', None)
        return obj.details


class AssetAuditEventPagination(CursorPagination):
    ordering = 'timestamp'
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


@swagger_auto_schema(
    methods=['GET'],
    responses={200: 'The asset audit events'},
)
@api_view(['GET'])
@permission_classes([IsApproved])
def asset_audit_events(request: Request) -> Response:
    queryset = AuditRecord.objects.filter(record_type__in=['add_asset', 'update_asset'])

    query_serializer = AssetAuditEventQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)

    # Time range filtering
    before = query_serializer.validated_data['before']
    after = query_serializer.validated_data['after']
    if before:
        queryset = queryset.filter(timestamp__lte=before)
    if after:
        queryset = queryset.filter(timestamp__gte=after)

    paginator = AssetAuditEventPagination()
    if query_serializer.validated_data['reverse_order']:
        paginator.ordering = '-timestamp'
    results_page = paginator.paginate_queryset(queryset=queryset, request=request)
    serializer = AssetAuditEventResponseSerializer(results_page, many=True)
    return paginator.get_paginated_response(serializer.data)
