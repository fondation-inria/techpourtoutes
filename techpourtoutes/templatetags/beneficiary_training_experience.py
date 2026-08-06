from django import template

from ..models.training_experience import training_experience_slots

register = template.Library()


@register.filter
def as_training_experience_slots(training_experiences):
    return training_experience_slots(training_experiences)
