import pytest
from django.urls import reverse

CHANGELIST = "admin:techpourtoutes_formation_changelist"


@pytest.mark.django_db
def test_formation_page_lists_the_schools_teaching_it(verified_admin_client, formation):
    url = reverse("admin:techpourtoutes_formation_change", args=[formation.pk])
    content = verified_admin_client.get(url).content.decode()
    assert "Lycée Voltaire" in content


@pytest.mark.django_db
def test_formation_changelist_shows_the_record_count(
    verified_admin_client, formation, higher_ed_formation
):
    response = verified_admin_client.get(reverse(CHANGELIST))
    content = response.content.decode()
    assert response.context["stats"]["total"]["total"] == 2
    assert "Formations" in content
    assert "derniers jours" not in content
