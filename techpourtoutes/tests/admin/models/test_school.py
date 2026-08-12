import pytest
from django.urls import reverse

CHANGELIST = "admin:techpourtoutes_school_changelist"


@pytest.mark.django_db
def test_school_page_lists_the_formations_it_teaches(verified_admin_client, formation):
    school = formation.schools.get()
    url = reverse("admin:techpourtoutes_school_change", args=[school.pk])
    content = verified_admin_client.get(url).content.decode()
    assert "Spécialité mathématiques" in content


@pytest.mark.django_db
def test_school_changelist_shows_the_record_count(verified_admin_client, school, higher_ed_school):
    response = verified_admin_client.get(reverse(CHANGELIST))
    content = response.content.decode()
    assert response.context["stats"]["total"]["total"] == 2
    assert "Établissements" in content
    # Imported data: a monthly import would make "+N sur 30 derniers jours" meaningless.
    assert "derniers jours" not in content
