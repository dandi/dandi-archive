from corsheaders.signals import check_request_enabled


def cors_allow_anyone_read_only(sender, request, **kwargs):
    """Allow any read-only request from any origin."""
    return request.method in ('GET', 'HEAD', 'OPTIONS')


check_request_enabled.connect(cors_allow_anyone_read_only)
