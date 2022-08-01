import logging

from allauth.socialaccount.models import SocialAccount
from dandischema.models import Dandiset as PydanticDandiset
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, F, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.db.utils import IntegrityError
from django.http import Http404
from django.utils.decorators import method_decorator
from drf_yasg.utils import no_body, swagger_auto_schema
from guardian.decorators import permission_required_or_403
from guardian.shortcuts import assign_perm, get_objects_for_user
from guardian.utils import get_40x_or_None
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.viewsets import ReadOnlyModelViewSet

from dandiapi.api.mail import send_ownership_change_emails
from dandiapi.api.models import Dandiset, Version
from dandiapi.api.tasks import unembargo_dandiset
from dandiapi.api.views.common import DANDISET_PK_PARAM, DandiPagination
from dandiapi.api.views.serializers import (
    CreateDandisetQueryParameterSerializer,
    DandisetDetailSerializer,
    DandisetListSerializer,
    DandisetQueryParameterSerializer,
    UserSerializer,
    VersionMetadataSerializer,
)


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
            elif ordering.endswith('name'):
                # name refers to the name of the most recent version, so a subquery is required
                latest_version = Version.objects.filter(dandiset=OuterRef('pk')).order_by(
                    '-created'
                )[:1]
                queryset = queryset.annotate(name=Subquery(latest_version.values('metadata__name')))
                return queryset.order_by(ordering)
            elif ordering.endswith('modified'):
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
            elif ordering.endswith('size'):
                latest_version = Version.objects.filter(dandiset=OuterRef('pk')).order_by(
                    '-created'
                )[:1]
                queryset = queryset.annotate(
                    size=Subquery(
                        latest_version.annotate(size=Sum('assets__blob__size')).values('size')
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
        if self.action == 'list':
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
        except ValueError:
            raise Http404('Not a valid identifier.')
        self.kwargs[self.lookup_url_kwarg] = lookup_value

        dandiset = super().get_object()
        if dandiset.embargo_status != Dandiset.EmbargoStatus.OPEN:
            if not self.request.user.is_authenticated:
                # Clients must be authenticated to access it
                raise NotAuthenticated()
            if not self.request.user.has_perm('owner', dandiset):
                # The user does not have ownership permission
                raise PermissionDenied()
        return dandiset

    @swagger_auto_schema(
        query_serializer=DandisetQueryParameterSerializer(),
        responses={200: DandisetListSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        dandisets = self.paginate_queryset(self.filter_queryset(qs))

        # Query versions, to supply size/count of assets.
        base_query = (
            Version.objects.select_related('dandiset')
            .annotate(
                num_assets=Count('assets'),
                total_size=(
                    Coalesce(Sum('assets__blob__size'), 0)
                    + Coalesce(Sum('assets__embargoed_blob__size'), 0)
                    + Coalesce(Sum('assets__zarr__size'), 0)
                ),
            )
            .filter(dandiset__in=dandisets)
            .order_by('-version', '-modified')
        )

        latest_dandiset_version = (
            Version.objects.exclude(version='draft')
            .order_by('-version')
            .filter(dandiset_id=OuterRef('dandiset_id'))
            .values('version')[:1]
        )
        published = (
            base_query.exclude(version='draft')
            .alias(latest=Subquery(latest_dandiset_version))
            .filter(version=F('latest'))
        )
        drafts = base_query.filter(version='draft')

        # Union with drafts
        versions = published.union(drafts).order_by('dandiset_id', '-version')

        # Organize draft and most recently published for each dandiset.
        # Because of above query, a max of 1 of each (per dandiset) will be present.
        dandisets_to_versions = {}
        for version in versions.iterator():
            version: Version

            if version.dandiset_id not in dandisets_to_versions:
                dandisets_to_versions[version.dandiset_id] = {'draft': None, 'published': None}

            entry = dandisets_to_versions[version.dandiset_id]
            if version.version == 'draft' and entry['draft'] is None:
                entry['draft'] = version
            elif entry['published'] is None:
                entry['published'] = version

        serializer = DandisetListSerializer(
            dandisets, many=True, context={'dandisets': dandisets_to_versions}
        )
        return self.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        request_body=VersionMetadataSerializer(),
        query_serializer=CreateDandisetQueryParameterSerializer(),
        responses={200: DandisetDetailSerializer()},
        operation_summary='Create a new dandiset.',
        operation_description='',
    )
    def create(self, request: Request):
        """Create a new dandiset."""
        serializer = VersionMetadataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query_serializer = CreateDandisetQueryParameterSerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        if query_serializer.validated_data['embargo']:
            embargo_status = Dandiset.EmbargoStatus.EMBARGOED
        else:
            embargo_status = Dandiset.EmbargoStatus.OPEN

        name = serializer.validated_data['name']
        metadata = serializer.validated_data['metadata']
        # Strip away any computed fields
        metadata = Version.strip_metadata(metadata)

        # Only inject a schemaVersion and default contributor field if they are
        # not specified in the metadata
        metadata = {
            'schemaKey': 'Dandiset',
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
            'contributor': [
                {
                    'name': f'{request.user.last_name}, {request.user.first_name}',
                    'email': request.user.email,
                    'roleName': ['dcite:ContactPerson'],
                    'schemaKey': 'Person',
                    'affiliation': [],
                    'includeInCitation': True,
                },
            ],
            # TODO: move this into dandischema
            'access': [
                {
                    'schemaKey': 'AccessRequirements',
                    'status': 'dandi:OpenAccess'
                    if embargo_status == Dandiset.EmbargoStatus.OPEN
                    else 'dandi:EmbargoedAccess',
                }
            ],
            **metadata,
        }
        # Run the metadata through the pydantic model to automatically include any boilerplate
        # like the access or repository fields
        metadata = PydanticDandiset.unvalidated(**metadata).json_dict()

        if 'identifier' in serializer.validated_data['metadata']:
            identifier = serializer.validated_data['metadata']['identifier']
            if identifier and not request.user.is_superuser:
                return Response(
                    'Creating a dandiset for a given identifier '
                    f'({identifier} was provided) is admin only operation.',
                    status=403,
                )
            if identifier.startswith('DANDI:'):
                identifier = identifier[6:]
            try:
                dandiset = Dandiset(id=int(identifier), embargo_status=embargo_status)
            except ValueError:
                return Response(f'Invalid Identifier {identifier}', status=400)
        else:
            dandiset = Dandiset(embargo_status=embargo_status)
        try:
            # Without force_insert, Django will try to UPDATE an existing dandiset if one exists.
            # We want to throw an error if a dandiset already exists.
            dandiset.save(force_insert=True)
        except IntegrityError as e:
            # https://stackoverflow.com/questions/25368020/django-deduce-duplicate-key-exception-from-integrityerror
            # https://www.postgresql.org/docs/13/errcodes-appendix.html
            # Postgres error code 23505 == unique_violation
            if e.__cause__.pgcode == '23505':
                return Response(f'Dandiset {dandiset.identifier} Already Exists', status=400)
            raise e

        logging.info(
            'Created dandiset %s given request with name=%s and metadata=%s',
            dandiset.identifier,
            name,
            metadata,
        )

        assign_perm('owner', request.user, dandiset)

        # Create new draft version
        version = Version(
            dandiset=dandiset,
            name=name,
            metadata=metadata,
            version='draft',
            status=Version.Status.PENDING,
        )
        version.save()

        serializer = DandisetDetailSerializer(instance=dandiset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[DANDISET_PK_PARAM],
    )
    @method_decorator(permission_required_or_403('owner', (Dandiset, 'pk', 'dandiset__pk')))
    def destroy(self, request, dandiset__pk):
        """
        Delete a dandiset.

        Deletes a dandiset. Only dandisets without published versions are deletable.
        """
        dandiset: Dandiset = self.get_object()

        if dandiset.versions.exclude(version='draft').exists():
            return Response(
                'Cannot delete dandisets with published versions.',
                status=status.HTTP_403_FORBIDDEN,
            )

        dandiset.delete()
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

        if dandiset.embargo_status != Dandiset.EmbargoStatus.EMBARGOED:
            return Response('Dandiset not embargoed', status=status.HTTP_400_BAD_REQUEST)

        unembargo_dandiset.delay(dandiset.pk)
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
    # TODO move these into a viewset
    @action(methods=['GET', 'PUT'], detail=True)
    def users(self, request, dandiset__pk):
        dandiset = self.get_object()
        if request.method == 'PUT':
            # Verify that the user is currently an owner
            response = get_40x_or_None(request, ['owner'], dandiset, return_403=True)
            if response:
                return response

            serializer = UserSerializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)

            def get_user_or_400(username):
                # SocialAccount uses the generic JSONField instead of the PostGres JSONFIELD,
                # so it is not empowered to do a more powerful query like:
                # SocialAccount.objects.get(extra_data__login=username)
                # We resort to doing this awkward search instead.
                for social_account in SocialAccount.objects.filter(extra_data__icontains=username):
                    if social_account.extra_data['login'] == username:
                        return social_account.user
                else:
                    try:
                        return User.objects.get(username=username)
                    except ObjectDoesNotExist:
                        raise ValidationError(f'User {username} not found')

            owners = [
                get_user_or_400(username=owner['username']) for owner in serializer.validated_data
            ]
            if len(owners) < 1:
                raise ValidationError('Cannot remove all draft owners')

            removed_owners, added_owners = dandiset.set_owners(owners)
            dandiset.save()

            send_ownership_change_emails(dandiset, removed_owners, added_owners)

        owners = []
        for owner in dandiset.owners:
            try:
                owner = SocialAccount.objects.get(user=owner)
                owner_dict = {'username': owner.extra_data['login']}
                if 'name' in owner.extra_data:
                    owner_dict['name'] = owner.extra_data['name']
                owners.append(owner_dict)
            except SocialAccount.DoesNotExist:
                # Just in case some users aren't using social accounts, have a fallback
                owners.append(
                    {'username': owner.username, 'name': f'{owner.first_name} {owner.last_name}'}
                )
        return Response(owners, status=status.HTTP_200_OK)
