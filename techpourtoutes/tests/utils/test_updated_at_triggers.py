from datetime import UTC, datetime

import pytest
from django.db import connection

from techpourtoutes.models import School
from techpourtoutes.utils.updated_at_triggers import install_updated_at_triggers

pytestmark = pytest.mark.django_db

LAST_WEEK = datetime(2026, 10, 27, tzinfo=UTC)

TABLES_WITHOUT_THE_TRIGGER = """
    SELECT columns.table_name
    FROM information_schema.columns
    WHERE columns.table_schema = current_schema()
        AND columns.column_name = 'updated_at'
        AND columns.table_name LIKE 'techpourtoutes\\_%'
        AND NOT EXISTS (
            SELECT FROM information_schema.triggers
            WHERE triggers.event_object_table = columns.table_name
                AND triggers.trigger_name = 'set_updated_at'
        )
"""


def _update_date(school):
    school.refresh_from_db()
    return school.updated_at


def _tables_without_the_trigger():
    with connection.cursor() as cursor:
        cursor.execute(TABLES_WITHOUT_THE_TRIGGER)
        return [table for (table,) in cursor.fetchall()]


def test_an_update_that_changes_a_row_moves_its_update_date(school):
    before = school.updated_at

    School.objects.filter(pk=school.pk).update(name="Lycée Victor Hugo")

    assert _update_date(school) > before


def test_an_update_that_changes_nothing_keeps_its_update_date(school):
    """`QuerySet.update()` and the imports' `bulk_create` bypass `save()`, and its `auto_now`."""
    before = school.updated_at

    School.objects.filter(pk=school.pk).update(name="Lycée Voltaire")

    assert _update_date(school) == before


def test_an_update_date_written_by_hand_is_kept(school):
    School.objects.filter(pk=school.pk).update(updated_at=LAST_WEEK)

    assert _update_date(school) == LAST_WEEK


def test_every_table_with_an_update_date_has_the_trigger():
    assert _tables_without_the_trigger() == []


def test_installing_the_triggers_again_restores_a_missing_one():
    with connection.cursor() as cursor:
        cursor.execute("DROP TRIGGER set_updated_at ON techpourtoutes_school")

    install_updated_at_triggers(connection)

    assert _tables_without_the_trigger() == []
