from __future__ import annotations

from rest_framework.authentication import TokenAuthentication


class BearerTokenAuthentication(TokenAuthentication):
    """
    To support not only DRF specific but also a standard oauth2 "Bearer" Authorization.

    Supporting both "token" and "Bearer" authorization requests is similar to GitHub behavior:
    See https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api?apiVersion=2022-11-28

    The recipe from https://github.com/encode/django-rest-framework//commit/ffdac0d93619b7ec6039b94ce0e563f0330faeb1
    """

    keyword = 'Bearer'
