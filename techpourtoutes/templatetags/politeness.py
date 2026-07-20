from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def politeness(context, vous_form, tu_form):
    condition = context.get("is_coalition_page") or context.get("is_pro")
    return vous_form if condition else tu_form
