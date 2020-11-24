from __future__ import annotations

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http.response import HttpResponseBase
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response


# TODO: put this somewhere more appropriate
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


@swagger_auto_schema(
    methods=['GET', 'POST'],
    responses={200: 'The user token'},
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def auth_token_view(request: Request) -> HttpResponseBase:
    if request.method == 'GET':
        token = get_object_or_404(Token, user=request.user)
    elif request.method == 'POST':
        Token.objects.filter(user=request.user).delete()
        token = Token.objects.create(user=request.user)
    return Response(token.key)
