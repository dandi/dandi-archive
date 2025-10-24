from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param
from rest_framework.viewsets import ReadOnlyModelViewSet

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.services import audit
from dandiapi.api.services.exceptions import DandiError
from dandiapi.api.services.permissions.dandiset import get_visible_dandisets, is_dandiset_owner
from dandiapi.api.views.pagination import DandiPagination
from dandiapi.api.views.serializers import DandisetIdentifierField
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus
from dandiapi.zarr.tasks import ingest_zarr_archive

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User
    from django.db.models.query import QuerySet

logger = logging.getLogger(__name__)


class ZarrFileCreationSerializer(serializers.Serializer):
    path = serializers.CharField()
    base64md5 = serializers.CharField()


class ZarrDeleteFileRequestSerializer(serializers.Serializer):
    path = serializers.CharField()


class ZarrArchiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZarrArchive
        read_only_fields = [
            'zarr_id',
            'status',
            'checksum',
            'file_count',
            'size',
        ]
        fields = ['name', 'dandiset', *read_only_fields]

    dandiset = serializers.PrimaryKeyRelatedField(
        queryset=Dandiset.objects.all(),
        pk_field=DandisetIdentifierField(),
    )

    def __init__(self, instance=None, data=serializers.empty, **kwargs):
        super().__init__(instance=instance, data=data, **kwargs)

        # If this was loaded via ".get_serializer", then the request is available in context
        self.user: User | AnonymousUser | None = (
            self._context['request'].user if 'request' in self._context else None
        )

        # A user is only necessary for validating input, but not to serialize output
        if self.user is not None:
            # Set the queryset here, before it's actually evaluated
            self.fields['dandiset'].queryset = get_visible_dandisets(self.user)

    def validate_dandiset(self, dandiset: Dandiset) -> Dandiset:
        if self.user is None:
            raise ValueError('Serializer user not set')
        if not is_dandiset_owner(dandiset, self.user):
            raise PermissionDenied
        if dandiset.unembargo_in_progress:
            raise DandiError(
                message='Cannot add zarr to dandiset during unembargo',
                http_status_code=status.HTTP_400_BAD_REQUEST,
            )
        return dandiset


class ZarrListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZarrArchive
        read_only_fields = [
            'zarr_id',
            'status',
            'checksum',
            'file_count',
            'size',
        ]
        fields = ['name', 'dandiset', *read_only_fields]

    dandiset = serializers.RegexField(f'^{Dandiset.IDENTIFIER_REGEX}$')


class ZarrExploreInputSerializer(serializers.Serializer):
    after = serializers.CharField(default='')
    prefix = serializers.CharField(default='')
    limit = serializers.IntegerField(min_value=0, max_value=1000, default=1000)
    download = serializers.BooleanField(default=False)


class ZarrExploreOutputSerializer(serializers.Serializer):
    class ResultsSerializer(serializers.Serializer):
        Key = serializers.CharField()
        LastModified = serializers.CharField()
        ETag = serializers.CharField()
        Size = serializers.IntegerField(min_value=0)

    next = serializers.CharField(default=None)
    results = serializers.ListField(child=ResultsSerializer())


class ZarrListQuerySerializer(serializers.Serializer):
    dandiset = serializers.RegexField(Dandiset.IDENTIFIER_REGEX, required=False)
    name = serializers.CharField(required=False)


class ZarrViewSet(ReadOnlyModelViewSet):
    serializer_class = ZarrArchiveSerializer
    pagination_class = DandiPagination

    queryset = ZarrArchive.objects.select_related('dandiset').order_by('created').all()
    lookup_field = 'zarr_id'
    lookup_value_regex = ZarrArchive.UUID_REGEX

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()

        # Filter zarrs to those that are contained by dandisets visible to the user
        return qs.filter(dandiset__in=get_visible_dandisets(self.request.user))

    @swagger_auto_schema(
        query_serializer=ZarrListQuerySerializer,
        responses={200: ZarrListSerializer(many=True)},
        operation_summary='List zarr archives.',
    )
    def list(self, request, *args, **kwargs):
        query_serializer = ZarrListQuerySerializer(data=self.request.query_params)
        query_serializer.is_valid(raise_exception=True)
        data = query_serializer.validated_data
        queryset: QuerySet[ZarrArchive] = self.get_queryset()

        # Add filters from query parameters
        if 'dandiset' in data:
            queryset = queryset.filter(dandiset=int(data['dandiset'].lstrip('0')))
        if 'name' in data:
            queryset = queryset.filter(name=data['name'])

        # Final response
        queryset = self.paginate_queryset(queryset)
        serializer = ZarrListSerializer(queryset, many=True)
        return self.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        request_body=ZarrArchiveSerializer,
        responses={200: ZarrArchiveSerializer},
        operation_summary='Create a new zarr archive.',
        operation_description='',
    )
    def create(self, request):
        """Create a new zarr archive."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            try:
                zarr_archive: ZarrArchive = serializer.save()
            except IntegrityError as e:
                raise ValidationError('Zarr already exists') from e

            audit.create_zarr(
                dandiset=serializer.validated_data['dandiset'],
                user=request.user,
                zarr_archive=zarr_archive,
            )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='POST',
        request_body=no_body,
        responses={
            # Note: Having proper None results in no documentation in /swagger
            204: 'None - expected normal return without any content',
            400: ZarrArchive.INGEST_ERROR_MSG,
        },
        operation_summary='Finalize a zarr archive, dispatching async checksum computation.',
        operation_description='',
    )
    @action(methods=['POST'], url_path='finalize', detail=True)
    def finalize(self, request, zarr_id):
        """Finalize a zarr archive."""
        queryset = self.get_queryset().select_for_update(of=['self'])
        with transaction.atomic():
            zarr_archive: ZarrArchive = get_object_or_404(queryset, zarr_id=zarr_id)
            if not is_dandiset_owner(zarr_archive.dandiset, self.request.user):
                # The user does not have ownership permission
                raise PermissionDenied

            # Don't ingest if already ingested/ingesting
            if zarr_archive.status != ZarrArchiveStatus.PENDING:
                return Response(ZarrArchive.INGEST_ERROR_MSG, status=status.HTTP_400_BAD_REQUEST)

            zarr_archive.status = ZarrArchiveStatus.UPLOADED
            zarr_archive.save()

            audit.finalize_zarr(
                dandiset=zarr_archive.dandiset, user=request.user, zarr_archive=zarr_archive
            )

        # Dispatch task
        ingest_zarr_archive.delay(zarr_id=zarr_archive.zarr_id)
        return Response(None, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        method='GET',
        responses={
            200: 'Listing of s3 objects',
            302: 'Redirect to an object in S3',
        },
        query_serializer=ZarrExploreInputSerializer,
    )
    @action(methods=['HEAD', 'GET'], detail=True)
    def files(self, request, zarr_id: str):
        """List files in a zarr archive."""
        zarr_archive = get_object_or_404(ZarrArchive, zarr_id=zarr_id)
        serializer = ZarrExploreInputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        # The root path for this zarr in s3
        # This will contain a trailing slash, due to the empty string argument
        base_path = zarr_archive.s3_path('')

        # Retrieve and join query params
        limit = serializer.validated_data['limit']
        download = serializer.validated_data['download']

        raw_prefix = serializer.validated_data['prefix'].lstrip('/')
        full_prefix = (base_path + raw_prefix).rstrip('/')

        raw_after = serializer.validated_data['after'].lstrip('/')
        after = (base_path + raw_after).rstrip('/') if raw_after else ''

        # Note: S3 will 404 if the file does not exist.
        if request.method == 'HEAD':
            return HttpResponseRedirect(zarr_archive.storage.url(full_prefix, http_method='HEAD'))
        if download:
            return HttpResponseRedirect(zarr_archive.storage.url(zarr_archive.s3_path(raw_prefix)))

        # Retrieve file listing
        listing = zarr_archive.storage.s3_client.list_objects_v2(
            Bucket=zarr_archive.storage.bucket_name,
            Prefix=full_prefix,
            StartAfter=after,
            MaxKeys=limit,
        )

        # Map/filter listing
        results = [
            {
                'Key': obj['Key'].removeprefix(base_path),
                'LastModified': obj['LastModified'],
                'ETag': obj['ETag'].strip('"'),
                'Size': obj['Size'],
            }
            for obj in listing.get('Contents', [])
        ]

        # Create next listing if necessary
        next_link = None
        if listing['IsTruncated']:
            url = self.request.build_absolute_uri()
            next_link = replace_query_param(url, 'after', results[-1]['Key'])

        # Construct serializer and return
        return Response(
            ZarrExploreOutputSerializer(
                instance={
                    'next': next_link,
                    'results': results,
                }
            ).data
        )

    @swagger_auto_schema(
        request_body=ZarrFileCreationSerializer(),
        responses={
            200: ZarrFileCreationSerializer,
            400: ZarrArchive.INGEST_ERROR_MSG,
        },
        operation_summary='Request to upload files to a zarr archive.',
        operation_description='',
    )
    @files.mapping.post
    def create_files(self, request, zarr_id):
        """Start an upload of files to a zarr archive."""
        queryset = self.get_queryset().select_for_update(of=['self'])
        with transaction.atomic():
            zarr_archive: ZarrArchive = get_object_or_404(queryset, zarr_id=zarr_id)
            if zarr_archive.status in [ZarrArchiveStatus.UPLOADED, ZarrArchiveStatus.INGESTING]:
                return Response(ZarrArchive.INGEST_ERROR_MSG, status=status.HTTP_400_BAD_REQUEST)

            # Deny if the user doesn't have ownership permission
            if not is_dandiset_owner(zarr_archive.dandiset, self.request.user):
                raise PermissionDenied

            serializer = ZarrFileCreationSerializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            paths = serializer.validated_data

            # Generate presigned urls
            logger.info('Beginning upload to zarr archive %s', zarr_archive.zarr_id)
            urls = [
                zarr_archive.storage.generate_presigned_put_object_url(
                    zarr_archive.s3_path(o['path']),
                    content_md5=o['base64md5'],
                    tags={'embargoed': 'true'} if zarr_archive.embargoed else None,
                )
                for o in paths
            ]

            # Set status back to pending, since with these URLs the zarr could have been changed
            zarr_archive.mark_pending()
            zarr_archive.save()

            audit.upload_zarr_chunks(
                dandiset=zarr_archive.dandiset,
                user=request.user,
                zarr_archive=zarr_archive,
                paths=[p['path'] for p in paths],
            )

        # Return presigned urls
        logger.info(
            'Presigned %d URLs to upload to zarr archive %s', len(urls), zarr_archive.zarr_id
        )
        return Response(urls, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=ZarrDeleteFileRequestSerializer(many=True),
        responses={
            200: ZarrArchiveSerializer(many=True),
            400: ZarrArchive.INGEST_ERROR_MSG,
        },
        operation_summary='Delete files from a zarr archive.',
    )
    @files.mapping.delete
    def delete_files(self, request, zarr_id):
        """Delete files from a zarr archive."""
        queryset = self.get_queryset().select_for_update()
        with transaction.atomic():
            zarr_archive: ZarrArchive = get_object_or_404(queryset, zarr_id=zarr_id)
            if zarr_archive.status in [ZarrArchiveStatus.UPLOADED, ZarrArchiveStatus.INGESTING]:
                return Response(ZarrArchive.INGEST_ERROR_MSG, status=status.HTTP_400_BAD_REQUEST)

            if not is_dandiset_owner(zarr_archive.dandiset, self.request.user):
                # The user does not have ownership permission
                raise PermissionDenied
            serializer = ZarrDeleteFileRequestSerializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            paths = [file['path'] for file in serializer.validated_data]
            zarr_archive.delete_files(paths)

            audit.delete_zarr_chunks(
                dandiset=zarr_archive.dandiset,
                user=request.user,
                zarr_archive=zarr_archive,
                paths=paths,
            )

        return Response(None, status=status.HTTP_204_NO_CONTENT)
