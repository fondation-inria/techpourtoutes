from pytest_django.plugin import pytest_collection_modifyitems as sort_as_django_does


def test_transactional_tests_run_after_the_tests_sharing_the_database(request):
    items = list(request.session.items)

    sort_as_django_does(items)

    assert items == request.session.items
