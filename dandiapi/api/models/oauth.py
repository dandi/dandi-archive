from fnmatch import fnmatch

from django.core.exceptions import ValidationError
from django.db import models
from oauth2_provider.models import AbstractApplication


class ProductionApplication(AbstractApplication):
    """
    Custom OAuth Toolkit `Application` model to override the
    `skip_authorization` default.
    """

    # The default value of `skip_authorization` in `AbstractApplication` is
    # `False`; we override that default here for production.
    skip_authorization = models.BooleanField(default=True)


class StagingApplication(AbstractApplication):
    """
    Custom OAuth Toolkit `Application` model to allow wildcards to be used in redirect URIs.

    This is ONLY used in staging; a more standard `oauth2_provider.models.Application`
    variant is used in production and local development.
    """

    # The default value of `skip_authorization` in `AbstractApplication` is `False`; we
    # override that default here for staging.
    skip_authorization = models.BooleanField(default=True)

    def clean(self):
        """
        Validate model fields.

        Overrides this method to ignore URL format errors so we can support wildcards.
        """
        try:
            super().clean()
        except ValidationError as e:
            # don't validate URLs so we can use wilcards too
            if 'Enter a valid URL.' not in str(e):
                raise e

    def redirect_uri_allowed(self, uri):
        """Check whether or not `uri` is a valid redirect_uri using wildcard matching."""
        for allowed_uri in self.redirect_uris.split():
            if fnmatch(uri, allowed_uri):
                return True
        return False
