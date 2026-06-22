from unittest.mock import patch

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_account_page_shows_communication_checkbox_checked_when_synced(client, pro):
    client.force_login(pro)
    content = client.get(reverse("account")).content.decode()
    assert "Je veux recevoir ponctuellement des nouvelles de TechPourToutes" in content
    assert "account-communication-card" in content
    assert "checked" in content


@pytest.mark.django_db
def test_account_communication_opt_in_enables_brevo_sync(client, pro):
    pro.brevo_sync_enabled = False
    pro.save()
    client.force_login(pro)

    response = client.post(reverse("account_communication"), data={"newsletter_consent": "on"})

    assert response.status_code == 200
    pro.refresh_from_db()
    assert pro.brevo_sync_enabled is True


@pytest.mark.django_db
def test_account_communication_opt_out_disables_brevo_sync(client, pro):
    client.force_login(pro)

    response = client.post(reverse("account_communication"), data={})

    assert response.status_code == 200
    pro.refresh_from_db()
    assert pro.brevo_sync_enabled is False


@pytest.mark.django_db(transaction=True)
def test_account_communication_opt_out_dispatches_delete(client, pro):
    client.force_login(pro)

    with patch("techpourtoutes.signals.delete_brevo_contact_task") as delete_task:
        client.post(reverse("account_communication"), data={})

    delete_task.delay.assert_called_once_with(str(pro.pk), 42)
