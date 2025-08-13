from __future__ import annotations

from .heroku_production import *

# NOTE: The staging settings uses a custom OAuth toolkit `Application` model
# (`StagingApplication`) to allow for wildcards in OAuth redirect URIs (to support Netlify branch
# deploy previews, etc). Note that both the custom `StagingApplication` and default
# `oauth2_provider.models.Application` will have Django database models and will show up on the
# Django admin, but only one of them will be in active use depending on the environment
# the API server is running in (production/local or staging).
OAUTH2_PROVIDER_APPLICATION_MODEL = 'api.StagingApplication'
