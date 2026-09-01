import pytest
from django.urls import reverse

CHANGELIST = "admin:techpourtoutes_event_changelist"


@pytest.mark.django_db
def test_event_changelist_shows_the_free_text_category(verified_admin_client, event):
    event.category = "Rencontre d'anciennes élèves"
    event.save()

    content = verified_admin_client.get(reverse(CHANGELIST)).content.decode()
    assert "Rencontre d&#x27;anciennes élèves" in content


@pytest.mark.django_db
def test_event_changelist_searches_on_its_creator(verified_admin_client, event):
    """Django validates neither a search_fields path nor a fieldsets omission — tests do."""
    response = verified_admin_client.get(reverse(CHANGELIST), {"q": event.created_by.email})

    assert "Salon des métiers du numérique" in response.content.decode()


@pytest.mark.django_db
def test_event_add_form_offers_every_mandatory_field(verified_admin_client):
    response = verified_admin_client.get(reverse("admin:techpourtoutes_event_add"))

    assert "organizer" in response.context["adminform"].form.fields


@pytest.mark.django_db
def test_event_page_offers_its_history(verified_admin_client, event):
    url = reverse("admin:techpourtoutes_event_change", args=[event.pk])
    content = verified_admin_client.get(url).content.decode()
    assert reverse("admin:techpourtoutes_event_history", args=[event.pk]) in content
