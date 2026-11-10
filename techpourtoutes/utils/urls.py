from django.utils.http import url_has_allowed_host_and_scheme


def safe_url(request, candidate):
    """`candidate` when it stays on this site, so that following it is no open redirect;
    an empty string otherwise."""
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return candidate
    return ""
