from __future__ import annotations

from typing import TYPE_CHECKING

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Max, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.db.models.query_utils import Q
from django.http import Http404
from django.utils.decorators import method_decorator
from drf_yasg.utils import no_body, swagger_auto_schema
from guardian.decorators import permission_required_or_403
from guardian.shortcuts import get_objects_for_user
from guardian.utils import get_40x_or_None
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.viewsets import ReadOnlyModelViewSet

from dandiapi.api.asset_paths import get_root_paths_many
from dandiapi.api.mail import send_ownership_change_emails
from dandiapi.api.models import Dandiset, Version
from dandiapi.api.services import audit
from dandiapi.api.services.dandiset import create_dandiset, delete_dandiset
from dandiapi.api.services.embargo import kickoff_dandiset_unembargo
from dandiapi.api.services.embargo.exceptions import (
    DandisetUnembargoInProgressError,
    UnauthorizedEmbargoAccessError,
)
from dandiapi.api.views.common import DANDISET_PK_PARAM
from dandiapi.api.views.pagination import DandiPagination
from dandiapi.api.views.serializers import (
    CreateDandisetQueryParameterSerializer,
    DandisetDetailSerializer,
    DandisetListSerializer,
    DandisetQueryParameterSerializer,
    DandisetSearchQueryParameterSerializer,
    DandisetSearchResultListSerializer,
    UserSerializer,
    VersionMetadataSerializer,
)
from dandiapi.search.models import AssetSearch

if TYPE_CHECKING:
    from rest_framework.request import Request


class DandisetFilterBackend(filters.OrderingFilter):
    ordering_fields = ['id', 'name', 'modified', 'size']
    ordering_description = (
        'Which field to use when ordering the results. '
        'Options are id, -id, name, -name, modified, -modified, size and -size.'
    )

    def filter_queryset(self, request, queryset, view):
        orderings = self.get_ordering(request, queryset, view)
        if orderings:
            ordering = orderings[0]
            # ordering can be either 'created' or '-created', so test for both
            if ordering.endswith('id'):
                return queryset.order_by(ordering)
            if ordering.endswith('name'):
                # name refers to the name of the most recent version, so a subquery is required
                latest_version = Version.objects.filter(dandiset=OuterRef('pk')).order_by(
                    '-created'
                )[:1]
                queryset = queryset.annotate(name=Subquery(latest_version.values('metadata__name')))
                return queryset.order_by(ordering)
            if ordering.endswith('modified'):
                # modified refers to the modification timestamp of the most
                # recent version, so a subquery is required
                latest_version = Version.objects.filter(dandiset=OuterRef('pk')).order_by(
                    '-created'
                )[:1]
                # get the `modified` field of the most recent version.
                # '_version' is appended because the Dandiset model already has a `modified` field
                queryset = queryset.annotate(
                    modified_version=Subquery(latest_version.values('modified'))
                )
                return queryset.order_by(f'{ordering}_version')
            if ordering.endswith('size'):
                latest_version = Version.objects.filter(dandiset=OuterRef('pk')).order_by(
                    '-created'
                )[:1]
                queryset = queryset.annotate(
                    size=Subquery(
                        latest_version.annotate(
                            size=Coalesce(Sum('assets__blob__size'), 0)
                            + Coalesce(Sum('assets__zarr__size'), 0)
                        ).values('size')
                    )
                )
                return queryset.order_by(ordering)
        return queryset


class DandisetViewSet(ReadOnlyModelViewSet):
    serializer_class = DandisetDetailSerializer
    pagination_class = DandiPagination
    filter_backends = [filters.SearchFilter, DandisetFilterBackend]
    search_fields = ['versions__metadata']

    lookup_value_regex = Dandiset.IDENTIFIER_REGEX
    # This is to maintain consistency with the auto-generated names shown in swagger.
    lookup_url_kwarg = 'dandiset__pk'

    def get_queryset(self):
        # Only include embargoed dandisets which belong to the current user
        queryset = Dandiset.objects
        if self.action in ['list', 'search']:
            queryset = Dandiset.objects.visible_to(self.request.user).order_by('created')

            query_serializer = DandisetQueryParameterSerializer(data=self.request.query_params)
            query_serializer.is_valid(raise_exception=True)

            # TODO: This will filter the dandisets list if there is a query parameter user=me.
            # This is not a great solution but it is needed for the My Dandisets page.
            user_kwarg = query_serializer.validated_data.get('user')
            if user_kwarg == 'me':
                # Replace the original, rather inefficient queryset with a more specific one
                queryset = get_objects_for_user(
                    self.request.user, 'owner', Dandiset, with_superuser=False
                ).order_by('created')

            show_draft: bool = query_serializer.validated_data['draft']
            show_empty: bool = query_serializer.validated_data['empty']
            show_embargoed: bool = query_serializer.validated_data['embargoed']

            # Return early if attempting to access embargoed data without authentication
            if show_embargoed and not self.request.user.is_authenticated:
                raise UnauthorizedEmbargoAccessError

            if not show_draft:
                # Only include dandisets that have more than one version, i.e. published dandisets.
                queryset = queryset.annotate(version_count=Count('versions')).filter(
                    version_count__gt=1
                )
            if not show_empty:
                # Only include dandisets that have assets in their most recent version.
                most_recent_version = (
                    Version.objects.filter(dandiset=OuterRef('pk'))
                    .order_by('created')
                    .annotate(asset_count=Count('assets'))[:1]
                )
                queryset = queryset.annotate(
                    draft_asset_count=Subquery(most_recent_version.values('asset_count'))
                )
                queryset = queryset.filter(draft_asset_count__gt=0)
            if not show_embargoed:
                queryset = queryset.filter(embargo_status='OPEN')
        return queryset

    def get_object(self):
        # Alternative to path converters, which DRF doesn't support
        # https://docs.djangoproject.com/en/3.0/topics/http/urls/#registering-custom-path-converters

        lookup_url = self.kwargs[self.lookup_url_kwarg]
        try:
            lookup_value = int(lookup_url)
        except ValueError as e:
            raise Http404('Not a valid identifier.') from e
        self.kwargs[self.lookup_url_kwarg] = lookup_value

        dandiset = super().get_object()
        if dandiset.embargo_status != Dandiset.EmbargoStatus.OPEN:
            if not self.request.user.is_authenticated:
                # Clients must be authenticated to access it
                raise NotAuthenticated
            if not self.request.user.has_perm('owner', dandiset):
                # The user does not have ownership permission
                raise PermissionDenied
        return dandiset

    @staticmethod
    def _get_dandiset_to_version_map(dandisets):
        """Map Dandiset IDs to that dandiset's draft and most recently published version."""
        relevant_versions = (
            Version.objects.select_related('dandiset')
            .filter(dandiset__in=dandisets)
            .order_by('-version', '-modified')
        )

        # This query sums the size and file count for root paths, and groups by the version_id,
        # ensuring that the queryset is unique w.r.t the version_id. For some reason, the
        # `order_by` clause is necessary to ensure this grouping
        version_stats = {
            entry['version_id']: entry
            for entry in get_root_paths_many(versions=relevant_versions)
            .values('version_id')
            .annotate(total_size=Sum('aggregate_size'), num_assets=Sum('aggregate_files'))
            .order_by()
        }

        def annotate_version(version: Version):
            """Annotate a version with its aggregate stats."""
            stats = version_stats.get(version.id, {'total_size': 0, 'num_assets': 0})
            version.total_size = stats['total_size']
            version.num_assets = stats['num_assets']

        # Create a map from dandiset IDs to their draft and published versions
        dandisets_to_versions = {}

        # Annotate and store all draft versions
        drafts = relevant_versions.filter(version='draft')
        for version in drafts:
            annotate_version(version)
            dandisets_to_versions[version.dandiset_id] = {
                'published': None,
                'draft': version,
            }

        # This query retrieves the versions with the max id for every dandiset_id. Since version id
        # is a autoincrementing field, it maps directly to the most recently published version.
        latest_published = Version.objects.filter(
            id__in=(
                relevant_versions.values('dandiset_id')
                .exclude(version='draft')
                .annotate(id=Max('id'))
                .values_list('id', flat=True)
            )
        )
        for version in latest_published:
            annotate_version(version)
            dandisets_to_versions[version.dandiset_id]['published'] = version

        return dandisets_to_versions

    @swagger_auto_schema(
        auto_schema=None,
        query_serializer=DandisetSearchQueryParameterSerializer,
        responses={200: DandisetSearchResultListSerializer(many=True)},
    )
    @action(methods=['GET'], detail=False)
    def search(self, request, *args, **kwargs):
        query_serializer = DandisetSearchQueryParameterSerializer(data=self.request.query_params)
        query_serializer.is_valid(raise_exception=True)
        query_filters = query_serializer.to_query_filters()
        relevant_assets = AssetSearch.objects.all()
        for query_filter in query_filters.values():
            relevant_assets = relevant_assets.filter(query_filter)
        qs = self.get_queryset()
        dandisets = self.filter_queryset(qs).filter(id__in=relevant_assets.values('dandiset_id'))
        dandisets = self.paginate_queryset(dandisets)
        dandisets_to_versions = self._get_dandiset_to_version_map(dandisets)
        dandisets_to_asset_counts = (
            AssetSearch.objects.values('dandiset_id')
            .filter(dandiset_id__in=[dandiset.id for dandiset in dandisets])
            .annotate(
                **{
                    query_filter_name: Count('asset_id', filter=query_filter_q)
                    for query_filter_name, query_filter_q in query_filters.items()
                    if query_filter_q != Q()
                }
            )
        )
        dandisets_to_asset_counts = {
            item['dandiset_id']: {
                field_name: item[field_name] for field_name in item if field_name != 'dandiset_id'
            }
            for item in dandisets_to_asset_counts
        }
        serializer = DandisetSearchResultListSerializer(
            dandisets,
            many=True,
            context={'dandisets': dandisets_to_versions, 'asset_counts': dandisets_to_asset_counts},
        )
        return self.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        query_serializer=DandisetQueryParameterSerializer,
        responses={200: DandisetListSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        dandisets = self.paginate_queryset(self.filter_queryset(qs))
        dandisets_to_versions = self._get_dandiset_to_version_map(dandisets)
        serializer = DandisetListSerializer(
            dandisets, many=True, context={'dandisets': dandisets_to_versions}
        )
        return self.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        request_body=VersionMetadataSerializer,
        query_serializer=CreateDandisetQueryParameterSerializer,
        responses={200: DandisetDetailSerializer},
        operation_summary='Create a new dandiset.',
        operation_description='',
    )
    def create(self, request: Request):
        """Create a new dandiset."""
        serializer = VersionMetadataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query_serializer = CreateDandisetQueryParameterSerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        identifier = None
        if 'identifier' in serializer.validated_data['metadata']:
            identifier = serializer.validated_data['metadata']['identifier']
            if identifier.startswith('DANDI:'):
                identifier = identifier[6:]

            try:
                identifier = int(identifier)
            except ValueError:
                return Response(f'Invalid Identifier {identifier}', status=400)

        dandiset, _ = create_dandiset(
            user=request.user,
            identifier=identifier,
            embargo=query_serializer.validated_data['embargo'],
            version_name=serializer.validated_data['name'],
            version_metadata=serializer.validated_data['metadata'],
        )

        serializer = DandisetDetailSerializer(instance=dandiset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[DANDISET_PK_PARAM],
    )
    def destroy(self, request, dandiset__pk):
        """
        Delete a dandiset.

        Deletes a dandiset. Only dandisets without published versions are deletable.
        """
        delete_dandiset(user=request.user, dandiset=self.get_object())
        return Response(None, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        methods=['POST'],
        manual_parameters=[DANDISET_PK_PARAM],
        request_body=no_body,
        responses={
            200: 'Dandiset unembargoing dispatched',
            400: 'Dandiset not embargoed',
        },
        operation_summary='Unembargo a dandiset.',
        operation_description=(
            'Unembargo an embargoed dandiset. Only permitted for owners and admins'
            '. If the embargo status is OPEN or UNEMBARGOING, an HTTP 400 is returned.'
        ),
    )
    @action(methods=['POST'], detail=True)
    @method_decorator(permission_required_or_403('owner', (Dandiset, 'pk', 'dandiset__pk')))
    def unembargo(self, request, dandiset__pk):
        dandiset: Dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
        kickoff_dandiset_unembargo(user=request.user, dandiset=dandiset)

        return Response(None, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='GET',
        manual_parameters=[DANDISET_PK_PARAM],
        responses={200: UserSerializer(many=True)},
        operation_summary='Get owners of a dandiset.',
        operation_description='',
    )
    @swagger_auto_schema(
        method='PUT',
        manual_parameters=[DANDISET_PK_PARAM],
        request_body=UserSerializer(many=True),
        responses={
            200: UserSerializer(many=True),
            400: 'User not found, or cannot remove all owners',
        },
        operation_summary='Set owners of a dandiset.',
        operation_description='Set the owners of a dandiset. The user performing this action must\
                               be an owner of the dandiset themself.',
    )
    # TODO: move these into a viewset
    @action(methods=['GET', 'PUT'], detail=True)
    def users(self, request, dandiset__pk):  # noqa: C901
        dandiset: Dandiset = self.get_object()
        if request.method == 'PUT':
            if dandiset.unembargo_in_progress:
                raise DandisetUnembargoInProgressError

            # Verify that the user is currently an owner
            response = get_40x_or_None(request, ['owner'], dandiset, return_403=True)
            if response:
                return response

            serializer = UserSerializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)

            # Ensure not all owners removed
            if not serializer.validated_data:
                raise ValidationError('Cannot remove all draft owners')

            # Get all owners that have the provided username in one of the two possible locations
            usernames = [owner['username'] for owner in serializer.validated_data]
            user_owners = list(User.objects.filter(username__in=usernames))
            socialaccount_owners = list(
                SocialAccount.objects.select_related('user').filter(extra_data__login__in=usernames)
            )

            # Check that all owners were found
            if len(user_owners) + len(socialaccount_owners) < len(usernames):
                username_set = {
                    *(user.username for user in user_owners),
                    *(owner.extra_data['login'] for owner in socialaccount_owners),
                }

                # Raise exception on first username in list that's not found
                for username in usernames:
                    if username not in username_set:
                        raise ValidationError(f'User {username} not found')

            # All owners found
            with transaction.atomic():
                owners = user_owners + [acc.user for acc in socialaccount_owners]
                removed_owners, added_owners = dandiset.set_owners(owners)
                dandiset.save()

                if removed_owners or added_owners:
                    audit.change_owners(
                        dandiset=dandiset,
                        user=request.user,
                        removed_owners=removed_owners,
                        added_owners=added_owners,
                    )

            send_ownership_change_emails(dandiset, removed_owners, added_owners)

        owners = []
        for owner_user in dandiset.owners:
            try:
                owner_account = SocialAccount.objects.get(user=owner_user)
                owner_dict = {'username': owner_account.extra_data['login']}
                if 'name' in owner_account.extra_data:
                    owner_dict['name'] = owner_account.extra_data['name']
                owners.append(owner_dict)
            except SocialAccount.DoesNotExist:
                # Just in case some users aren't using social accounts, have a fallback
                owners.append(
                    {
                        'username': owner_user.username,
                        'name': f'{owner_user.first_name} {owner_user.last_name}',
                    }
                )
        return Response(owners, status=status.HTTP_200_OK)
