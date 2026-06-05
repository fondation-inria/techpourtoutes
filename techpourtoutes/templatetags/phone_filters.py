from django import template

register = template.Library()


@register.filter
def phone_national(phone):
    if not phone:
        return ""
    return phone.as_national
