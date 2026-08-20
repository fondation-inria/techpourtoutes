from django import template
from django.urls import reverse
from waffle import switch_is_active

register = template.Library()


@register.simple_tag
def home_url():
    if switch_is_active("beneficiary_mode"):
        return reverse("home")
    return reverse("coalition_home")


@register.simple_tag
def beneficiary_home_url():
    """Empty when the beneficiary site is not routed, so callers can hide the link."""
    if switch_is_active("beneficiary_mode"):
        return reverse("home")
    return ""
