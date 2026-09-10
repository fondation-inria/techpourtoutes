import pytest
from django.urls import get_resolver

URLCONFS = [
    "techpourtoutes.urls_common",
    "techpourtoutes.urls_beneficiary",
    "techpourtoutes.urls_coalition",
]


@pytest.mark.parametrize("urlconf", URLCONFS)
def test_routes_end_with_a_slash(urlconf):
    """A slash-less route 404s on the slash-terminated URL: APPEND_SLASH never strips one."""
    routes = [str(pattern.pattern) for pattern in get_resolver(urlconf).url_patterns]
    assert [route for route in routes if route and not route.endswith("/")] == []
