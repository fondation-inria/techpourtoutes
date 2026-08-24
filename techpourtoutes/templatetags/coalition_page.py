from urllib.parse import urlparse

from django import template
from django.urls import Resolver404, resolve

from techpourtoutes.urls_coalition import urlpatterns as coalition_urlpatterns

register = template.Library()

URL_COALITION_NAMES = {pattern.name for pattern in coalition_urlpatterns}


@register.simple_tag(takes_context=True)
def is_coalition_page(context, path=None):
    if path is None and "is_pro" in context:
        return bool(context["is_pro"])
    url_match = _resolve_url_match(context, path)
    return url_match is not None and url_match.url_name in URL_COALITION_NAMES


def _resolve_url_match(context, path):
    if not path:
        return context["request"].resolver_match
    try:
        return resolve(urlparse(path).path)
    except Resolver404:
        return None
