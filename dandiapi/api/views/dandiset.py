from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from allauth.socialaccount.models import SocialAccount
from dandischema.conf import get_instance_config
from django.contrib.auth.models import User
from django.contrib.postgres.lookups import Unaccent
from django.db import transaction
from django.db.models import Count, Max, OuterRef, QuerySet, Subquery, Sum, TextField
from django.db.models.functions import Cast, Coalesce
from django.db.models.query_utils import Q
from drf_yasg import openapi
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from dandiapi.api.asset_paths import get_root_paths_many
from dandiapi.api.mail import send_ownership_change_emails
from dandiapi.api.models import Dandiset, Version
from dandiapi.api.models.asset_paths import AssetPath
from dandiapi.api.models.dandiset import DandisetStar
from dandiapi.api.services import audit
from dandiapi.api.services.dandiset import (
    create_embargoed_dandiset,
    create_open_dandiset,
    delete_dandiset,
    star_dandiset,
    unstar_dandiset,
)
from dandiapi.api.services.embargo import kickoff_dandiset_unembargo
from dandiapi.api.services.embargo.exceptions import (
    DandisetUnembargoInProgressError,
    UnauthorizedEmbargoAccessError,
)
from dandiapi.api.services.exceptions import NotAllowedError, NotAuthenticatedError
from dandiapi.api.services.permissions.dandiset import (
    get_dandiset_owners,
    get_owned_dandisets,
    get_visible_dandisets,
    is_dandiset_owner,
    replace_dandiset_owners,
    require_dandiset_owner,
    require_dandiset_owner_or_403,
    require_dandiset_read_access,
)
from dandiapi.api.services.search import SearchSyntaxError, parse_search
from dandiapi.api.services.search.filters import apply_search_filters
from dandiapi.api.views.common import DANDISET_PK_PARAM, PAGINATION_PARAMS
from dandiapi.api.views.pagination import DandiPagination
from dandiapi.api.views.serializers import (
    CreateDandisetQueryParameterSerializer,
    DandisetDetailSerializer,
    DandisetListSerializer,
    DandisetQueryParameterSerializer,
    DandisetSearchQueryParameterSerializer,
    DandisetSearchResultListSerializer,
    DandisetUploadSerializer,
    UserSerializer,
    VersionMetadataSerializer,
)
from dandiapi.search.models import AssetSearch

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from typing import Any

    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser
    from rest_framework.request import Request

    from dandiapi.api.models.upload import Upload

DANDISET_ORDERING_FIELDS = ['id', 'name', 'modified', 'size', 'stars']

ORDERING_PARAM = openapi.Parameter(
    'ordering',
    openapi.IN_QUERY,
    'Which field to use when ordering the results. Options are '
    + ', '.join(f'{prefix}{field}' for field in DANDISET_ORDERING_FIELDS for prefix in ('', '-'))
    + '.',
    type=openapi.TYPE_STRING,
    required=False,
)


def get_readable_dandiset_or_404(request: Request, dandiset__pk: str) -> Dandiset:
    """Fetch a dandiset by ID, ensuring the requesting user is permitted to read it."""
    dandiset = get_object_or_404(Dandiset, pk=int(dandiset__pk))
    require_dandiset_read_access(dandiset, request.user)
    return dandiset


def _order_dandisets(
    dandisets: QuerySet[Dandiset], ordering_param: str | None
) -> QuerySet[Dandiset]:
    """
    Order a dandiset queryset by the requested field.

    The parameter is a comma separated list of fields, each optionally prefixed with `-` to
    reverse it, of which only the first recognized field is used. Unrecognized fields are
    ignored, leaving the queryset's existing ordering in place.

    All the orderable fields but `id` belong to the dandiset's most recent version, rather
    than to the dandiset itself, so they require a subquery.
    """
    orderings = [
        field.strip()
        for field in (ordering_param or '').split(',')
        if field.strip().lstrip('-') in DANDISET_ORDERING_FIELDS
    ]
    if not orderings:
        return dandisets

    # An ordering can be either 'created' or '-created', so test for both
    ordering = orderings[0]
    if ordering.endswith('id'):
        return dandisets.order_by(ordering)

    latest_version = Version.objects.filter(dandiset=OuterRef('pk')).order_by('-created')[:1]
    if ordering.endswith('name'):
        # name refers to the name of the most recent version, so a subquery is required
        return dandisets.annotate(name=Subquery(latest_version.values('metadata__name'))).order_by(
            ordering
        )
    if ordering.endswith('modified'):
        # modified refers to the modification timestamp of the most
        # recent version, so a subquery is required.
        # '_version' is appended because the Dandiset model already has a `modified` field
        return dandisets.annotate(
            modified_version=Subquery(latest_version.values('modified'))
        ).order_by(f'{ordering}_version')
    if ordering.endswith('size'):
        return dandisets.annotate(
            size=Subquery(
                latest_version.annotate(
                    size=Coalesce(
                        Sum(
                            'asset_paths__aggregate_size',
                            filter=~Q(asset_paths__path__contains='/'),
                        ),
                        0,
                    )
                ).values('size')
            )
        ).order_by(ordering)

    # Ordering by stars
    prefix = '-' if ordering.startswith('-') else ''
    return dandisets.annotate(stars_count=Count('stars')).order_by(f'{prefix}stars_count')


def _search_dandisets(
    dandisets: QuerySet[Dandiset],
    search_term: str | None,
    user: AbstractBaseUser | AnonymousUser,
) -> QuerySet[Dandiset]:
    """
    Filter a dandiset queryset down to those matching a search string.

    Gmail-style operators (e.g. species:mouse, created_after:2024-01-01) are parsed out of
    the search string and applied as structured filters. Anything left over (free text,
    including quoted phrases) flows through the full-text path. Any parse / validation
    problems surface as a 400.
    """
    if not search_term:
        return dandisets

    try:
        parsed = parse_search(search_term)
        dandisets = apply_search_filters(dandisets, parsed, user=user)
    except SearchSyntaxError as exc:
        raise ValidationError({'search': str(exc)}) from exc

    if not parsed.free_text:
        return dandisets

    # Build a Q object that requires all free-text words to be present
    q_filter = Q()
    for word in parsed.free_text:
        q_filter &= Q(search_field__icontains=word)

    # We must formulate the filter using a separate query first, as otherwise
    # the generated SQL is incompatible with previously generated clauses
    matching_dandiset_ids = (
        Version.objects.alias(search_field=Unaccent(Cast('metadata', TextField())))
        .filter(q_filter)
        .values_list('dandiset_id', flat=True)
        .distinct()
    )

    return dandisets.filter(id__in=matching_dandiset_ids)


def _listed_dandisets(request: Request, query: Mapping[str, Any]) -> QuerySet[Dandiset]:
    """Build the queryset of dandisets selected by the dandiset list query parameters."""
    dandisets = get_visible_dandisets(request.user).order_by('created')

    # TODO: This will filter the dandisets list if there is a query parameter user=me.
    # This is not a great solution but it is needed for the My Dandisets page.
    if query.get('user') == 'me':
        # Replace the original, rather inefficient queryset with a more specific one
        dandisets = get_owned_dandisets(request.user, include_superusers=False).order_by('created')

    show_draft: bool = query['draft']
    show_empty: bool = query['empty']
    show_embargoed: bool = query['embargoed']
    filter_starred: bool = query['starred']

    # Return early if attempting to access embargoed data without authentication
    if show_embargoed and not request.user.is_authenticated:
        raise UnauthorizedEmbargoAccessError

    if not show_draft:
        # Only include dandisets that have more than one version, i.e. published dandisets.
        dandisets = dandisets.annotate(version_count=Count('versions')).filter(version_count__gt=1)
    if not show_empty:
        # Get the most recent version of every dandiset in the queryset
        most_recent_versions = (
            Version.objects.filter(dandiset__in=dandisets)
            .order_by('dandiset_id', '-created')
            .distinct('dandiset_id')
        )

        # Use asset paths to determine which of these most recent versions are empty. This is
        # done by simply querying the table for any asset paths from any of the most recent
        # versions, and returning back the list of version IDs. This may seem like it
        # accomplishes nothing, but since asset paths only exist when assets on a version exist,
        # it filters out versions which have no assets (those that are empty).
        nonempty_version_ids = (
            AssetPath.objects.filter(version__in=most_recent_versions)
            .order_by()
            .distinct('version_id')
            .values_list('version_id', flat=True)
        )

        dandisets = dandisets.filter(versions__in=nonempty_version_ids)
    if not show_embargoed:
        dandisets = dandisets.filter(embargo_status='OPEN')
    if filter_starred:
        if not request.user.is_authenticated:
            raise NotAuthenticatedError(
                message='Must be authenticated to filter by starred dandisets.'
            )

        dandisets = dandisets.filter(stars__user=request.user).order_by('-stars__created')

    dandisets = _search_dandisets(dandisets, query.get('search'), request.user)
    return _order_dandisets(dandisets, request.query_params.get('ordering'))


def _get_dandiset_star_context(
    dandisets: Iterable[Dandiset], user: AbstractBaseUser | AnonymousUser
) -> dict[int, dict]:
    # Default value for all relevant dandisets
    dandisets_to_stars = {d.id: {'total': 0, 'starred_by_current_user': False} for d in dandisets}

    # Group the stars for these dandisets by the dandiset ID,
    # yielding pairs of (Dandiset ID, Star Count)
    dandiset_stars = (
        DandisetStar.objects.filter(dandiset__in=dandisets)
        .values_list('dandiset')
        .annotate(star_count=Count('id'))
        .order_by()
    )
    for dandiset_id, star_count in dandiset_stars:
        dandisets_to_stars[dandiset_id]['total'] = star_count

    # Only annotate dandisets as starred by current user if user is logged in
    if user.is_anonymous:
        return dandisets_to_stars

    # Filter previous query to current user stars
    user_starred_dandisets = dandiset_stars.filter(user=user)
    for dandiset_id, _ in user_starred_dandisets:
        dandisets_to_stars[dandiset_id]['starred_by_current_user'] = True

    return dandisets_to_stars


def _get_dandiset_to_version_map(dandisets: Iterable[Dandiset]) -> dict[int, dict]:
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


def _list_dandisets(request: Request) -> Response:
    query_serializer = DandisetQueryParameterSerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)

    paginator = DandiPagination()
    dandisets = paginator.paginate_queryset(
        _listed_dandisets(request, query_serializer.validated_data), request=request
    )
    serializer = DandisetListSerializer(
        dandisets,
        many=True,
        context={
            'dandisets': _get_dandiset_to_version_map(dandisets),
            'stars': _get_dandiset_star_context(dandisets, request.user),
        },
    )
    return paginator.get_paginated_response(serializer.data)


def _create_dandiset(request: Request) -> Response:
    """Create a new dandiset."""
    serializer = VersionMetadataSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    query_serializer = CreateDandisetQueryParameterSerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)

    identifier = None
    if 'identifier' in serializer.validated_data['metadata']:
        identifier = serializer.validated_data['metadata']['identifier']
        identifier = identifier.removeprefix(f'{get_instance_config().instance_name}:')

        try:
            identifier = int(identifier)
        except ValueError:
            return Response(f'Invalid Identifier {identifier}', status=400)

    if query_serializer.validated_data['embargo']:
        dandiset, _ = create_embargoed_dandiset(
            user=request.user,
            identifier=identifier,
            version_name=serializer.validated_data['name'],
            version_metadata=serializer.validated_data['metadata'],
            funding_source=query_serializer.validated_data.get('funding_source'),
            award_number=query_serializer.validated_data.get('award_number'),
            embargo_end_date=query_serializer.validated_data['embargo_end_date'],
        )
    else:
        dandiset, _ = create_open_dandiset(
            user=request.user,
            identifier=identifier,
            version_name=serializer.validated_data['name'],
            version_metadata=serializer.validated_data['metadata'],
        )

    return Response(DandisetDetailSerializer(instance=dandiset).data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='GET',
    query_serializer=DandisetQueryParameterSerializer,
    manual_parameters=[ORDERING_PARAM, *PAGINATION_PARAMS],
    responses={200: DandisetListSerializer(many=True)},
    operation_summary='List dandisets.',
)
@swagger_auto_schema(
    method='POST',
    request_body=VersionMetadataSerializer,
    query_serializer=CreateDandisetQueryParameterSerializer,
    responses={200: DandisetDetailSerializer},
    operation_summary='Create a new dandiset.',
    operation_description='',
)
@api_view(['GET', 'HEAD', 'POST'])
def dandiset_list_view(request: Request) -> Response:
    if request.method == 'POST':
        return _create_dandiset(request)
    return _list_dandisets(request)


@swagger_auto_schema(
    method='GET',
    auto_schema=None,
    query_serializer=DandisetSearchQueryParameterSerializer,
    responses={200: DandisetSearchResultListSerializer(many=True)},
)
@api_view(['GET', 'HEAD'])
def dandiset_search_view(request: Request) -> Response:
    query_serializer = DandisetSearchQueryParameterSerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)
    query_filters = query_serializer.to_query_filters()

    relevant_assets = AssetSearch.objects.all()
    for query_filter in query_filters.values():
        relevant_assets = relevant_assets.filter(query_filter)

    paginator = DandiPagination()
    dandisets = paginator.paginate_queryset(
        _listed_dandisets(request, query_serializer.validated_data).filter(
            id__in=relevant_assets.values('dandiset_id')
        ),
        request=request,
    )

    dandisets_to_asset_counts = {
        item['dandiset_id']: {
            field_name: item[field_name] for field_name in item if field_name != 'dandiset_id'
        }
        for item in AssetSearch.objects.values('dandiset_id')
        .filter(dandiset_id__in=[dandiset.id for dandiset in dandisets])
        .annotate(
            **{
                query_filter_name: Count('asset_id', filter=query_filter_q)
                for query_filter_name, query_filter_q in query_filters.items()
                if query_filter_q != Q()
            }
        )
    }
    serializer = DandisetSearchResultListSerializer(
        dandisets,
        many=True,
        context={
            'dandisets': _get_dandiset_to_version_map(dandisets),
            'asset_counts': dandisets_to_asset_counts,
            'stars': _get_dandiset_star_context(dandisets, request.user),
        },
    )
    return paginator.get_paginated_response(serializer.data)


def _retrieve_dandiset(request: Request, dandiset__pk: str) -> Response:
    dandiset = get_readable_dandiset_or_404(request, dandiset__pk)
    serializer = DandisetDetailSerializer(instance=dandiset, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


def _destroy_dandiset(request: Request, dandiset__pk: str) -> Response:
    """
    Delete a dandiset.

    Deletes a dandiset. Only dandisets without published versions are deletable.
    """
    dandiset = get_readable_dandiset_or_404(request, dandiset__pk)
    delete_dandiset(user=request.user, dandiset=dandiset)
    return Response(None, status=status.HTTP_204_NO_CONTENT)


@swagger_auto_schema(
    method='GET',
    manual_parameters=[DANDISET_PK_PARAM],
    responses={200: DandisetDetailSerializer},
    operation_summary='Get a dandiset.',
)
@swagger_auto_schema(
    method='DELETE',
    manual_parameters=[DANDISET_PK_PARAM],
    operation_summary='Delete a dandiset.',
    operation_description=(
        'Deletes a dandiset. Only dandisets without published versions are deletable.'
    ),
)
@api_view(['GET', 'HEAD', 'DELETE'])
def dandiset_detail_view(request: Request, **kwargs) -> Response:
    if request.method == 'DELETE':
        return _destroy_dandiset(request, **kwargs)
    return _retrieve_dandiset(request, **kwargs)


@swagger_auto_schema(
    method='POST',
    operation_id='dandisets_unembargo',
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
@api_view(['POST'])
@require_dandiset_owner_or_403('dandiset__pk')
def dandiset_unembargo_view(request: Request, dandiset__pk: str) -> Response:
    dandiset: Dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
    kickoff_dandiset_unembargo(user=request.user, dandiset=dandiset)

    return Response(None, status=status.HTTP_200_OK)


def _set_dandiset_owners(request: Request, dandiset: Dandiset) -> None:
    if dandiset.unembargo_in_progress:
        raise DandisetUnembargoInProgressError

    # Verify that the user is currently an owner
    if not is_dandiset_owner(dandiset, request.user):
        raise NotAllowedError

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
        dandiset_locked = Dandiset.objects.select_for_update().get(pk=dandiset.pk)
        owners = user_owners + [acc.user for acc in socialaccount_owners]
        removed_owners, added_owners = replace_dandiset_owners(dandiset_locked, owners)
        dandiset_locked.save()

        if removed_owners or added_owners:
            audit.change_owners(
                dandiset=dandiset_locked,
                user=request.user,
                removed_owners=removed_owners,
                added_owners=added_owners,
            )

    send_ownership_change_emails(dandiset, removed_owners, added_owners)


def _serialize_dandiset_owners(request: Request, dandiset: Dandiset) -> list[dict]:
    owners = []
    for owner_user in get_dandiset_owners(dandiset):
        try:
            owner_account = SocialAccount.objects.get(user=owner_user)
            owner_dict = {'username': owner_account.extra_data['login']}
            owner_dict['name'] = owner_account.extra_data.get('name', None)
            owner_dict['email'] = (
                owner_account.extra_data['email']
                # Only logged-in users can see owners' email addresses
                if request.user.is_authenticated and 'email' in owner_account.extra_data
                else None
            )
            owners.append(owner_dict)
        except SocialAccount.DoesNotExist:
            # Just in case some users aren't using social accounts, have a fallback
            owners.append(
                {
                    'username': owner_user.username,
                    'name': f'{owner_user.first_name} {owner_user.last_name}',
                    'email': owner_user.email if request.user.is_authenticated else None,
                }
            )

    return owners


@swagger_auto_schema(
    method='GET',
    operation_id='dandisets_users_read',
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
    operation_description=(
        'Set the owners of a dandiset. The user performing this action must '
        'be an owner of the dandiset themself.'
    ),
)
@api_view(['GET', 'HEAD', 'PUT'])
def dandiset_users_view(request: Request, dandiset__pk: str) -> Response:
    dandiset = get_readable_dandiset_or_404(request, dandiset__pk)
    if request.method == 'PUT':
        _set_dandiset_owners(request, dandiset)

    return Response(_serialize_dandiset_owners(request, dandiset), status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='GET',
    operation_id='dandisets_uploads_read',
    manual_parameters=[DANDISET_PK_PARAM, *PAGINATION_PARAMS],
    request_body=no_body,
    responses={200: DandisetUploadSerializer(many=True)},
    operation_summary='List active/incomplete uploads in this dandiset.',
)
@swagger_auto_schema(
    method='DELETE',
    manual_parameters=[DANDISET_PK_PARAM],
    request_body=no_body,
    operation_summary='Delete all active/incomplete uploads in this dandiset.',
)
@api_view(['GET', 'HEAD', 'DELETE'])
def dandiset_uploads_view(request: Request, dandiset__pk: str) -> Response:
    dandiset = get_readable_dandiset_or_404(request, dandiset__pk)

    # Special case where a "safe" method is access restricted, due to the nature of uploads
    require_dandiset_owner(dandiset, request.user)

    if request.method == 'DELETE':
        dandiset.uploads.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    uploads: QuerySet[Upload] = dandiset.uploads.all()

    # Paginate and return
    paginator = DandiPagination()
    page = paginator.paginate_queryset(uploads, request=request)
    serializer = DandisetUploadSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@swagger_auto_schema(
    method='POST',
    manual_parameters=[DANDISET_PK_PARAM],
    request_body=no_body,
    responses={
        200: 'Dandiset starred successfully',
        401: 'Authentication required',
    },
    operation_summary='Star a dandiset.',
    operation_description='Star a dandiset. User must be authenticated.',
)
@swagger_auto_schema(
    method='DELETE',
    manual_parameters=[DANDISET_PK_PARAM],
    request_body=no_body,
    responses={
        200: 'Dandiset unstarred successfully',
        401: 'Authentication required',
    },
    operation_summary='Unstar a dandiset.',
    operation_description='Unstar a dandiset. User must be authenticated.',
)
@api_view(['POST', 'DELETE'])
def dandiset_star_view(request: Request, dandiset__pk: str) -> Response:
    dandiset = get_readable_dandiset_or_404(request, dandiset__pk)
    user = typing.cast('User', request.user)
    if request.method == 'POST':
        star_count = star_dandiset(user=user, dandiset=dandiset)
    else:
        star_count = unstar_dandiset(user=user, dandiset=dandiset)

    return Response({'count': star_count}, status=status.HTTP_200_OK)
