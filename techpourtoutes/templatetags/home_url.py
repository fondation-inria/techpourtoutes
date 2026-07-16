from django import template
from django.urls import reverse
from waffle import switch_is_active

register = template.Library()


@register.simple_tag
def home_url():
    if beneficiary_mode_active():
        return reverse("home")
    return reverse("coalition_home")


def beneficiary_mode_active():
    try:
        return switch_is_active("beneficiary_mode")
    except Exception:
        return False
