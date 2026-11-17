from contextlib import closing

import pytest
from django.db import connection
from pytest_django.plugin import pytest_collection_modifyitems as sort_as_django_does


def test_transactional_tests_run_after_the_tests_sharing_the_database(request):
    items = list(request.session.items)

    sort_as_django_does(items)

    assert items == request.session.items


@pytest.mark.django_db
def test_the_test_database_number_is_locked_until_the_suite_ends():
    base, number = connection.settings_dict["NAME"].rsplit("_", 1)
    params = {**connection.get_connection_params(), "dbname": "postgres"}

    with closing(connection.get_new_connection(params)) as other_session:
        with other_session.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(hashtext(%s), %s)", [base, int(number)])
            assert cursor.fetchone()[0] is False
