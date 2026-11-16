import importlib

import pytest
from django.apps import apps

from techpourtoutes.models import Event

from ..models.test_event import build_event

migration = importlib.import_module("techpourtoutes.migrations.0077_event_department_code")

pytestmark = pytest.mark.django_db


def test_existing_events_get_the_department_of_their_place(pro):
    build_event(pro, title="Brest", cog_code="29019").save()
    build_event(pro, title="En ligne").save()
    Event.objects.update(department_code="")

    migration.derive_department_codes(apps, None)

    assert dict(Event.objects.values_list("title", "department_code")) == {
        "Brest": "29",
        "En ligne": "",
    }
