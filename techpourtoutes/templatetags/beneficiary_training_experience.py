from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def current_year_training_experience_slot(context, training_experiences):
    if any(experience.is_current_school_year for experience in training_experiences):
        return ""
    html = render_to_string(
        "account/partials/beneficiary_training_experience_card.html",
        {"experience": None},
        request=context.get("request"),
    )
    return mark_safe(html)
