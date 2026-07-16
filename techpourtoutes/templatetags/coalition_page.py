from django import template

from techpourtoutes.urls_coalition import urlpatterns as coalition_urlpatterns

register = template.Library()

URL_COALITION_NAMES = {pattern.name for pattern in coalition_urlpatterns}


@register.simple_tag(takes_context=True)
def is_coalition_page(context):
    resolver_match = context["request"].resolver_match
    if resolver_match is None:
        return False
    return resolver_match.url_name in URL_COALITION_NAMES
