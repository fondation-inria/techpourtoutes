import pytest
from django.core import mail
from django.test import override_settings

from techpourtoutes.mailers import ConsortiumMailer
from techpourtoutes.models import Pro


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
    from techpourtoutes.models import Formation, TrainingExperience

    formation = Formation(onisep_id="9701", name="Master IA")
    formation.save()
    experience = TrainingExperience.objects.create(
        user=pro, school=higher_ed_school, formation=formation
    )
    ConsortiumMailer.new_training_ambassador(pro=pro, training_experience=experience)

    message = mail.outbox[0]
    assert message.to == ["training@example.com"]
    assert "Master IA" in message.body
    assert higher_ed_school.name in message.body


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
