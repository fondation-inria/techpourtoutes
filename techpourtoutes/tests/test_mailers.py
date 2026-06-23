import pytest
from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from techpourtoutes.mailers import CoalitionMailer, LoginMailer
from techpourtoutes.models import Pro


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", USE_BREVO=False)
def test_welcome_sends_email_to_pro(pro):
    CoalitionMailer.welcome(pro=pro, token="tok-abc")

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [pro.email]
    assert "Bienvenue" in message.subject
    assert pro.first_name in message.body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", USE_BREVO=False)
def test_welcome_includes_account_login_url(pro):
    CoalitionMailer.welcome(pro=pro, token="tok-abc")

    assert "/se-connecter/token/tok-abc" in mail.outbox[0].body


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    USE_BREVO=False,
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
    CoalitionMailer.new_pro(pro=pro, engagement=engagement)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [recipient]
    assert str(Pro.Engagement(engagement).label) in message.subject


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    USE_BREVO=False,
    COALITION_TRAINING_AMBASSADOR_RECIPIENTS=["training@example.com"],
)
def test_new_training_ambassador_includes_experience_in_body(pro, higher_ed_school):
    from techpourtoutes.models import TrainingExperience

    experience = TrainingExperience.objects.create(
        pro=pro, higher_ed_school=higher_ed_school, course="Master IA"
    )
    CoalitionMailer.new_training_ambassador(pro=pro, training_experience=experience)

    message = mail.outbox[0]
    assert message.to == ["training@example.com"]
    assert "Master IA" in message.body
    assert higher_ed_school.full_name in message.body


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    USE_BREVO=False,
    COALITION_WORK_AMBASSADOR_RECIPIENTS=["ambassador@example.com"],
)
def test_new_pro_includes_pro_details_in_body(pro):
    CoalitionMailer.new_pro(pro=pro, engagement=Pro.Engagement.WORK_AMBASSADOR)

    body = mail.outbox[0].body
    assert pro.first_name in body
    assert pro.last_name in body
    assert pro.email in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", USE_BREVO=False)
def test_login_send_link_sends_email_to_user(pro):
    LoginMailer.send_link(user=pro, token="tok-abc")

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [pro.email]
    assert message.subject == "Votre lien de connexion à TechPourToutes"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", USE_BREVO=False)
def test_login_send_link_body_contains_absolute_login_url(pro):
    LoginMailer.send_link(user=pro, token="tok-abc")

    expected_url = f"{settings.SITE_URL}{reverse('login_verify', args=['tok-abc'])}"
    assert expected_url in mail.outbox[0].body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", USE_BREVO=False)
def test_login_send_link_appends_next_url_when_provided(pro):
    LoginMailer.send_link(user=pro, token="tok-abc", next_url="/mon-compte/")

    body = mail.outbox[0].body
    assert "next=%2Fmon-compte%2F" in body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", USE_BREVO=False)
def test_login_send_link_omits_next_query_when_empty(pro):
    LoginMailer.send_link(user=pro, token="tok-abc")

    assert "next=" not in mail.outbox[0].body
