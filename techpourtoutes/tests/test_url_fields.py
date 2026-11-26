from django.apps import apps
from django.core.validators import URLValidator
from django.db import models


def test_url_fields_hold_every_url_the_validator_accepts():
    """Django's 200-character default is shorter than what `URLValidator` lets through, so a
    long link would pass the form and then fail on save."""
    short_url_fields = [
        f"{model.__name__}.{field.name}"
        for model in apps.get_app_config("techpourtoutes").get_models()
        for field in model._meta.get_fields()
        if isinstance(field, models.URLField) and field.max_length != URLValidator.max_length
    ]

    assert short_url_fields == []
