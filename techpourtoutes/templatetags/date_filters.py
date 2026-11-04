from datetime import date

from django import template
from django.utils.timesince import timesince

register = template.Library()


@register.filter
def time_ago(value):
    return f"il y a {timesince(value, depth=1)}"


@register.filter
def iso_date(value):
    """<input type="date"> only accepts YYYY-MM-DD, whatever the active locale."""
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return value or ""
