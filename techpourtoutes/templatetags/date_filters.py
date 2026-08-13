from datetime import date

from django import template

register = template.Library()


@register.filter
def iso_date(value):
    """<input type="date"> only accepts YYYY-MM-DD, whatever the active locale."""
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return value or ""
