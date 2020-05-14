from girder.exceptions import ValidationException
from girder.utility import setting_utilities


PUBLISH_API_URL = "dandi.publish_api_url"
PUBLISH_API_KEY = "dandi.publish_api_key"


@setting_utilities.default(PUBLISH_API_URL)
def _default_publish_api_url():
    return ""


@setting_utilities.default(PUBLISH_API_KEY)
def _default_publish_api_key():
    return ""


@setting_utilities.validator(PUBLISH_API_URL)
def _validate_url(url):
    if not isinstance(url["value"], str):
        raise ValidationException("The setting is not a string", "value")


@setting_utilities.validator(PUBLISH_API_KEY)
def _validate_key(key):
    if not isinstance(key["value"], str):
        raise ValidationException("The setting is not a string", "value")
