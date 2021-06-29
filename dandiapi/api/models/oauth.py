from fnmatch import fnmatch

from django.core.exceptions import ValidationError
from oauth2_provider.models import AbstractApplication


class StagingApplication(AbstractApplication):
    """
    Custom OAuth Toolkit `Application` model to allow wildcards to be used in redirect URIs.

    This is ONLY used in staging; the standard `oauth2_provider.models.Application` is used
    in production and local development.
    """

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
