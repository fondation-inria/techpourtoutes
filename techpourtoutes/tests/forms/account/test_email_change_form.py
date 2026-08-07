import pytest


@pytest.mark.django_db
def test_change_email_form_accepts_new_valid_email(pro):
    from techpourtoutes.forms import EmailChangeForm

    form = EmailChangeForm(data={"email": "nouvelle@example.com"}, user=pro)
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_change_email_form_rejects_current_email(pro):
    from techpourtoutes.forms import EmailChangeForm

    form = EmailChangeForm(data={"email": pro.email.upper()}, user=pro)
    assert not form.is_valid()
    assert "email" in form.errors


@pytest.mark.django_db
def test_change_email_form_rejects_email_used_by_another_account(pro, inactive_user):
    from techpourtoutes.forms import EmailChangeForm

    form = EmailChangeForm(data={"email": inactive_user.email}, user=pro)
    assert not form.is_valid()
    assert "email" in form.errors
