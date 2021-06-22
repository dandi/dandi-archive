import re
from django.core.exceptions import ValidationError
from oauth2_provider.models import AbstractApplication


class Application(AbstractApplication):
    # override URL validation
    def clean(self):
        try:
            super().clean()
        except ValidationError as e:
            # don't validate URLs so we can use regexes too
            if 'Enter a valid URL.' not in str(e):
                raise e

    def redirect_uri_allowed(self, uri):
        for allowed_uri in self.redirect_uris.split():
            if re.fullmatch(uri, allowed_uri):
                return True
        return False
