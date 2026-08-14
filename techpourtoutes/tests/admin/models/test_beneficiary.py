import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_beneficiary_page_lists_training_experiences(
    verified_admin_client, beneficiary, beneficiary_experience
):
    url = reverse("admin:techpourtoutes_beneficiary_change", args=[beneficiary.pk])
    content = verified_admin_client.get(url).content.decode()
    assert "Spécialité mathématiques" in content
    assert "Lycée Voltaire" in content
