import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.mailers import (
    AccountMailer,
    AuthMailer,
    ConsortiumMailer,
    ProMailer,
)
from techpourtoutes.models import Pro


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_welcome_sends_email_to_pro(pro):
    ProMailer.welcome(pro=pro, token="tok-abc")

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [pro.email]
    assert "Bienvenue" in message.subject
    assert pro.first_name in message.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_welcome_includes_account_login_url(pro):
    ProMailer.welcome(pro=pro, token="tok-abc")

    assert "/se-connecter/token/tok-abc" in mail.outbox[0].body


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    COALITION_INTERNSHIPS_RECIPIENTS=["internships@example.com"],
    COALITION_WORK_AMBASSADOR_RECIPIENTS=["ambassador@example.com"],
    COALITION_TRAINING_AMBASSADOR_RECIPIENTS=["training@example.com"],
    COALITION_SPONSOR_RECIPIENTS=["sponsor@example.com"],
)
@pytest.mark.parametrize(
    "engagement,recipient",
    [
        (Pro.Engagement.INTERNSHIPS, "internships@example.com"),
        (Pro.Engagement.WORK_AMBASSADOR, "ambassador@example.com"),
        (Pro.Engagement.SPONSOR, "sponsor@example.com"),
    ],
)
def test_new_pro_routes_to_engagement_recipient(pro, engagement, recipient):
    ConsortiumMailer.new_pro(pro=pro, engagement=engagement)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [recipient]
    assert str(Pro.Engagement(engagement).label) in message.subject


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    COALITION_TRAINING_AMBASSADOR_RECIPIENTS=["training@example.com"],
)
def test_new_training_ambassador_includes_experience_in_body(pro, higher_ed_school):
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience.objects.create(
        user=pro, higher_ed_school=higher_ed_school, course="Master IA"
    )
    ConsortiumMailer.new_training_ambassador(pro=pro, training_experience=experience)

    message = mail.outbox[0]
    assert message.to == ["training@example.com"]
    assert "Master IA" in message.body
    assert higher_ed_school.full_name in message.body


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    COALITION_WORK_AMBASSADOR_RECIPIENTS=["ambassador@example.com"],
)
def test_new_pro_includes_pro_details_in_body(pro):
    ConsortiumMailer.new_pro(pro=pro, engagement=Pro.Engagement.WORK_AMBASSADOR)

    body = mail.outbox[0].body
    assert pro.first_name in body
    assert pro.last_name in body
    assert pro.email in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_send_code_sends_email_to_user(pro):
    AuthMailer.login_code(user=pro, code="123456")

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [pro.email]
    assert message.subject == "Votre code de connexion à TechPourToutes"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_send_code_body_contains_the_code(pro):
    AuthMailer.login_code(user=pro, code="123456")

    assert "123456" in mail.outbox[0].body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_new_engagement_sends_email_to_pro(pro):
    ProMailer.new_engagement(pro=pro)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [pro.email]
    assert "Votre nouvelle demande d'engagement" in message.subject
    assert pro.first_name in message.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_welcome_attaches_its_brevo_tags(pro):
    ProMailer.welcome(pro=pro, token="tok-abc")

    assert mail.outbox[0].tags == ["utilisateur", "coalition", "mail de bienvenue"]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_login_code_attaches_its_brevo_tags(pro):
    AuthMailer.login_code(user=pro, code="123456")

    assert mail.outbox[0].tags == ["utilisateur", "mail de connexion"]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_sends_confirmation_email_with_vous_form_to_pro(pro):
    AccountMailer.deletion_confirmation(user=pro)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [pro.email]
    assert message.subject == "Confirmation de suppression de votre compte"
    assert pro.first_name in message.body
    assert "vous confirmons" in message.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_sends_confirmation_email_with_tu_form_to_beneficiary(beneficiary):
    AccountMailer.deletion_confirmation(user=beneficiary)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [beneficiary.email]
    assert message.subject == "Confirmation de suppression de ton compte"
    assert beneficiary.first_name in message.body
    assert "te confirmons" in message.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_email_includes_jobirl_information_for_pro_with_jobirl_account(pro):
    pro.jobirl_user_id = 12345
    pro.save()

    AccountMailer.deletion_confirmation(user=pro)

    body = mail.outbox[0].body

    assert "JobIRL" in body
    assert "e-mentorat@jobirl.com" in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_email_omits_jobirl_information_for_pro_without_jobirl_account(pro):
    AccountMailer.deletion_confirmation(user=pro)

    body = mail.outbox[0].body

    assert "JobIRL" not in body
    assert "e-mentorat@jobirl.com" not in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_email_includes_jobirl_information_for_beneficiary_with_jobirl_account(
    beneficiary,
):
    beneficiary.jobirl_user_id = 6789
    beneficiary.save()

    AccountMailer.deletion_confirmation(user=beneficiary)

    body = mail.outbox[0].body

    assert "JobIRL" in body
    assert "e-mentorat@jobirl.com" in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_email_omits_jobirl_information_for_beneficiary_without_jobirl_account(
    beneficiary,
):
    AccountMailer.deletion_confirmation(user=beneficiary)

    body = mail.outbox[0].body

    assert "JobIRL" not in body
    assert "e-mentorat@jobirl.com" not in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_delete_account_confirmation_attaches_its_brevo_tags(pro):
    AccountMailer.deletion_confirmation(user=pro)

    assert mail.outbox[0].tags == [
        "utilisateur",
        "suppression du compte",
    ]


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EXTERNAL_ACCOUNT_DELETION_RECIPIENTS=["dpo@example.com"],
)
def test_delete_account_request_sends_email_to_configured_recipients(pro):
    pro.jobirl_user_id = 12345
    pro.save()

    AccountMailer.request_external_account_deletion(user=pro)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]

    assert message.to == ["dpo@example.com"]
    assert message.subject == "Demande de suppression de données personnelles"

    body = message.body
    assert pro.first_name in body
    assert pro.last_name in body
    assert str(pro.jobirl_user_id) in body


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EXTERNAL_ACCOUNT_DELETION_RECIPIENTS=["dpo@example.com"],
)
def test_delete_account_request_attaches_its_brevo_tags(pro):
    AccountMailer.request_external_account_deletion(user=pro)

    assert mail.outbox[0].tags == [
        "interne",
        "suppression du compte",
    ]
