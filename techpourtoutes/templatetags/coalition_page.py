from urllib.parse import urlparse

from django import template
from django.urls import Resolver404, resolve
from waffle import switch_is_active

from techpourtoutes.urls_coalition import urlpatterns as coalition_urlpatterns

register = template.Library()

URL_COALITION_NAMES = {pattern.name for pattern in coalition_urlpatterns}


@register.simple_tag(takes_context=True)
def is_coalition_page(context, path=None):
    if not switch_is_active("beneficiary_mode"):
        return True
    return _is_coalition_url(_resolve_url_match(context, path))


def _is_coalition_url(url_match):
    return url_match is not None and url_match.url_name in URL_COALITION_NAMES


def _resolve_url_match(context, path):
    if not path:
        return context["request"].resolver_match
    try:
        return resolve(urlparse(path).path)
    except Resolver404:
        return None
