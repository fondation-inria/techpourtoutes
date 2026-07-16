from urllib.parse import urlparse

from django import template
from django.urls import Resolver404, resolve

from techpourtoutes.templatetags.home_url import beneficiary_mode_active
from techpourtoutes.urls_coalition import urlpatterns as coalition_urlpatterns

register = template.Library()

URL_COALITION_NAMES = {pattern.name for pattern in coalition_urlpatterns}


@register.simple_tag(takes_context=True)
def is_coalition_page(context, path=None):
    if not beneficiary_mode_active():
        return True

    if path:
        try:
            resolver_match = resolve(urlparse(path).path)
        except Resolver404:
            return False
    else:
        resolver_match = context["request"].resolver_match
    if resolver_match is None:
        return False
    return resolver_match.url_name in URL_COALITION_NAMES
