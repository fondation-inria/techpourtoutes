from django import template

register = template.Library()


@register.filter
def elided_pages(page):
    """Django elides around the current page, which a template cannot pass as an argument.

    One page on each side and one at each end keep the widget under seven items, so it fits
    a phone screen whatever the page count. Eliding around a page one step inside the range
    rather than around the current one costs nothing in the middle, and buys the first and
    last pages the third number they would otherwise lose to the edge.
    """
    paginator = page.paginator
    number = min(max(page.number, 2), paginator.num_pages - 1)
    return paginator.get_elided_page_range(number, on_each_side=1, on_ends=1)
