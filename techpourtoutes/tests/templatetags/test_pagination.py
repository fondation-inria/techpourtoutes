from django.core.paginator import Paginator

from techpourtoutes.templatetags.pagination import elided_pages


def test_the_range_is_elided_on_both_sides_of_the_current_page():
    page = Paginator(range(200), 15).get_page(7)

    assert list(elided_pages(page)) == [1, Paginator.ELLIPSIS, 6, 7, 8, Paginator.ELLIPSIS, 14]


def test_a_short_range_is_listed_whole():
    page = Paginator(range(30), 15).get_page(1)

    assert list(elided_pages(page)) == [1, 2]
