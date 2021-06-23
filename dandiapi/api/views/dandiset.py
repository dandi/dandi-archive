import logging

from allauth.socialaccount.models import SocialAccount
from django.db.models import OuterRef, Subquery
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
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.viewsets import ReadOnlyModelViewSet

from dandiapi.api.mail import send_ownership_change_emails
from dandiapi.api.models import Dandiset, Version, VersionMetadata
from dandiapi.api.views.common import DandiPagination
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
                # call reverse() so the default order puts more recently modified dandisets first
                return queryset.order_by(f'{ordering}_version')
        return queryset


class DandisetViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = DandisetDetailSerializer
    pagination_class = DandiPagination
    filter_backends = [filters.SearchFilter, DandisetFilterBackend]
    search_fields = ['versions__metadata__metadata']

    lookup_value_regex = Dandiset.IDENTIFIER_REGEX
    # This is to maintain consistency with the auto-generated names shown in swagger.
    lookup_url_kwarg = 'dandiset__pk'

    def get_queryset(self):
        # TODO: This will filter the dandisets list if there is a query parameter user=me.
        # This is not a great solution but it is needed for the My Dandisets page.
        queryset = Dandiset.objects.all().order_by('created')
        user_kwarg = self.request.query_params.get('user', None)
        if user_kwarg == 'me':
            return get_objects_for_user(self.request.user, 'owner', queryset, with_superuser=False)
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
    )
    def create(self, request):
        serializer = VersionMetadataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data['name']
        metadata = serializer.validated_data['metadata']

        version_metadata, created = VersionMetadata.objects.get_or_create(
            name=name,
            metadata=metadata,
        )
        if created:
            version_metadata.save()

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
        version = Version(dandiset=dandiset, metadata=version_metadata, version='draft')
        version.save()

        serializer = DandisetDetailSerializer(instance=dandiset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @method_decorator(permission_required_or_403('owner', (Dandiset, 'pk', 'dandiset__pk')))
    def destroy(self, request, dandiset__pk):
        dandiset: Dandiset = get_object_or_404(Dandiset, pk=dandiset__pk)

        dandiset.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(method='GET', responses={200: UserSerializer(many=True)})
    @swagger_auto_schema(
        method='PUT',
        request_body=UserSerializer(many=True),
        responses={
            200: UserSerializer(many=True),
            400: 'User not found, or cannot remove all owners',
        },
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
                try:
                    # SocialAccount uses the generic JSONField instead of the PostGres JSONFIELD,
                    # so it is not empowered to do a more powerful query like:
                    # SocialAccount.objects.get(extra_data__login=username)
                    # We resort to doing this awkward search instead.
                    for social_account in SocialAccount.objects.filter(
                        extra_data__icontains=username
                    ):
                        if social_account.extra_data['login'] == username:
                            return social_account.user
                    else:
                        raise SocialAccount.DoesNotExist()
                except SocialAccount.DoesNotExist:
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
                owners.append({'username': owner.username})
        return Response(owners, status=status.HTTP_200_OK)
