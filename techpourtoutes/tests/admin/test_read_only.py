import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_inline_rows_stylesheet_is_loaded(verified_admin_client, admin_pro, experience):
    """Without it, every inline row would repeat the row's own label above its columns."""
    url = reverse("admin:techpourtoutes_pro_change", args=[admin_pro.pk])
    content = verified_admin_client.get(url).content.decode()
    assert "css/admin_inlines.css" in content
