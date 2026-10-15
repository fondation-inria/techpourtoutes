import importlib

import pytest
from django.apps import apps
from waffle.models import Switch

migration = importlib.import_module("techpourtoutes.migrations.0061_delete_new_pro_features_switch")

pytestmark = pytest.mark.django_db


def test_the_new_pro_features_switch_is_deleted():
    Switch.objects.update_or_create(name="new_pro_features", defaults={"active": True})

    migration.delete_switch(apps, None)

    assert not Switch.objects.filter(name="new_pro_features").exists()


def test_other_switches_are_left_alone():
    Switch.objects.create(name="another_feature", active=True)

    migration.delete_switch(apps, None)

    assert Switch.objects.filter(name="another_feature").exists()
