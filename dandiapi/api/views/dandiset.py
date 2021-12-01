import logging

from allauth.socialaccount.models import SocialAccount
from dandischema.models import Dandiset as PydanticDandiset
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, OuterRef, Q, Subquery
from django.db.utils import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from guardian.decorators import permission_required_or_403
from guardian.shortcuts import assign_perm, get_objects_for_user
from guardian.utils import get_40x_or_None
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.viewsets import ReadOnlyModelViewSet

from dandiapi.api.mail import send_ownership_change_emails
from dandiapi.api.models import Dandiset, Version
from dandiapi.api.permissions import IsApprovedOrReadOnly
from dandiapi.api.views.common import DANDISET_PK_PARAM, DandiPagination
from dandiapi.api.views.serializers import (
    DandisetDetailSerializer,
    UserSerializer,
    VersionMetadataSerializer,
)


class DandisetFilterBackend(filters.OrderingFilter):
    ordering_fields = ['id', 'name', 'modified']
    ordering_description = (
        'Which field to use when ordering the results. '
        'Options are id, -id, name, -name, modified, and -modified.'
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
        return queryset


class DandisetViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsApprovedOrReadOnly]
    serializer_class = DandisetDetailSerializer
    pagination_class = DandiPagination
    filter_backends = [filters.SearchFilter, DandisetFilterBackend]
    search_fields = ['versions__metadata']

    lookup_value_regex = Dandiset.IDENTIFIER_REGEX
    # This is to maintain consistency with the auto-generated names shown in swagger.
    lookup_url_kwarg = 'dandiset__pk'

    def get_queryset(self):
        # TODO: This will filter the dandisets list if there is a query parameter user=me.
        # This is not a great solution but it is needed for the My Dandisets page.
        queryset = Dandiset.objects.all().order_by('created')
        if self.action == 'list':
            user_kwarg = self.request.query_params.get('user', None)
            if user_kwarg == 'me':
                queryset = get_objects_for_user(
                    self.request.user, 'owner', queryset, with_superuser=False
                )
            # Same deal for filtering out draft or empty dandisets
            show_draft = self.request.query_params.get('draft', 'true') == 'true'
            show_empty = self.request.query_params.get('empty', 'true') == 'true'

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

        return super().get_object()

    @swagger_auto_schema(
        request_body=VersionMetadataSerializer(),
        responses={200: DandisetDetailSerializer()},
        operation_summary='Create a new dandiset.',
        operation_description='',
    )
    def create(self, request):
        """Create a new dandiset."""
        serializer = VersionMetadataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

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
                dandiset = Dandiset(id=int(identifier))
            except ValueError:
                return Response(f'Invalid Identifier {identifier}', status=400)
        else:
            dandiset = Dandiset()
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
        dandiset: Dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)

        if dandiset.versions.filter(~Q(version='draft')).exists():
            return Response(
                'Cannot delete dandisets with published versions.',
                status=status.HTTP_403_FORBIDDEN,
            )

        dandiset.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)

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
        dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)
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
