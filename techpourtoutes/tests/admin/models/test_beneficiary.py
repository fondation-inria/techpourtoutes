import pytest
from django.urls import reverse

from techpourtoutes.models import SavedEvent


@pytest.mark.django_db
def test_beneficiary_page_lists_training_experiences(
    verified_admin_client, beneficiary, beneficiary_experience
):
    url = reverse("admin:techpourtoutes_beneficiary_change", args=[beneficiary.pk])
    content = verified_admin_client.get(url).content.decode()
    assert "Spécialité mathématiques" in content
    assert "Lycée Voltaire" in content


@pytest.mark.django_db
def test_beneficiary_page_lists_the_events_she_saved(verified_admin_client, beneficiary, event):
    SavedEvent.objects.toggle(event=event, beneficiary=beneficiary)

    url = reverse("admin:techpourtoutes_beneficiary_change", args=[beneficiary.pk])
    content = verified_admin_client.get(url).content.decode()

    assert "Salon des métiers du numérique" in content
    assert "Événements sauvegardés" in content


@pytest.mark.django_db
def test_beneficiary_page_shows_her_legal_representative_authorization(
    verified_admin_client, beneficiary, authorization
):
    url = reverse("admin:techpourtoutes_beneficiary_change", args=[beneficiary.pk])
    content = verified_admin_client.get(url).content.decode()

    assert "Autorisation de la personne responsable légale" in content
    assert "marie.petit@example.com" in content
    assert "en attente" in content
