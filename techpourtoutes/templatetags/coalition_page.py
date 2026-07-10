from django import template

from techpourtoutes.sitemaps import COALITION_PAGE_NAMES

register = template.Library()


@register.simple_tag(takes_context=True)
def is_coalition_page(context):
    resolver_match = context["request"].resolver_match
    if resolver_match is None:
        return False
    return resolver_match.url_name in COALITION_PAGE_NAMES
