from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.urls import Resolver404, resolve, reverse


def coalition_host_redirect(get_response):
    """Send the coalition vanity subdomain to the coalition pages of the main site."""

    def middleware(request):
        if request.get_host() != settings.COALITION_OLD_HOST:
            return get_response(request)
        return HttpResponsePermanentRedirect(f"{settings.SITE_URL}{_coalition_path(request)}")

    return middleware


def _coalition_path(request):
    path = f"/coalition{request.path}"
    try:
        resolve(path)
    except Resolver404:
        return reverse("coalition_home")
    return f"{path}?{request.GET.urlencode()}" if request.GET else path
