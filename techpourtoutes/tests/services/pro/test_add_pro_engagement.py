from unittest.mock import MagicMock, patch

import pytest
from django.core import mail

from techpourtoutes.forms import (
    ProAdditionalInformationForm,
    ProTrainingAmbassadorForm,
    ProWorkshopRequestForm,
)
from techpourtoutes.models import Pro
from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.pro.add_pro_engagement import AddProEngagement

REGISTER = "techpourtoutes.services.pro.create_mentor.RegisterUserOnJobirl"
NOTIFY_WORKSHOP = "techpourtoutes.services.pro.pro_engagement_mixin.notify_workshop_request_task"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def mail_recipients(settings):
    settings.COALITION_SPONSOR_RECIPIENTS = ["sponsor@example.com"]
    settings.COALITION_TRAINING_AMBASSADOR_RECIPIENTS = ["training@example.com"]


def _with_engagements(pro, *engagements):
    pro.engagements = list(engagements)
    pro.save()
    return pro


def _workshop_request_form(job_title="Enseignante"):
    answers = {
        "job_title": job_title,
        "structure_uai": "0750001A",
        "school_label": "Lycée Voltaire",
        "postal_code": "75005",
        "ateliers": ["future_of_tech"],
        "remark": "",
    }
    form = ProWorkshopRequestForm(data={f"workshop-{name}": v for name, v in answers.items()})
    assert form.is_valid()
    return form


def _add(pro, engagement, **screens):
    with patch(NOTIFY_WORKSHOP):
        return AddProEngagement(pro=pro, engagement=engagement, **screens)


def _sent_to(recipient):
    return [message for message in mail.outbox if recipient in message.to]


def test_add_pro_engagement_changes_nothing_she_is_not_eligible_for(pro):
    _with_engagements(pro, "mentor")

    result = _add(pro, Pro.Engagement.TRAINING_AMBASSADOR)

    assert "pas compatible" in result.errors[0]
    pro.refresh_from_db()
    assert pro.engagements == ["mentor"]
    assert mail.outbox == []


# ------------------- engagement -------------------


def test_add_pro_engagement_adds_it_with_what_she_completed(pro):
    form = ProAdditionalInformationForm(data={"structure_type": "company"}, pro=pro)
    assert form.is_valid()

    result = _add(pro, Pro.Engagement.SPONSOR, additional_information=form.cleaned_data)

    assert result.success
    pro.refresh_from_db()
    assert pro.engagements == ["sponsor"]
    assert (pro.structure_type, pro.structure_name) == ("company", "Inria")


def test_add_pro_engagement_tells_her_and_the_team(pro):
    _add(pro, Pro.Engagement.SPONSOR)

    subjects = [message.subject for message in _sent_to(pro.email)]
    assert "Votre nouvelle demande d'engagement auprès de TechPourToutes" in subjects
    assert len(_sent_to("sponsor@example.com")) == 1


def test_add_pro_engagement_registers_a_new_mentor_on_jobirl(pro):
    registered = MagicMock(success=True, failure=False, user_id=287565, token="tpt_abc")
    with patch(REGISTER, return_value=registered):
        result = _add(pro, Pro.Engagement.MENTOR)

    assert result.success
    pro.refresh_from_db()
    assert pro.engagements == ["mentor"]
    assert pro.jobirl_user_id == 287565


@pytest.mark.django_db(transaction=True)
def test_add_pro_engagement_saves_nothing_when_jobirl_refuses_the_mentor(pro):
    refused = MagicMock(
        success=False,
        failure=True,
        errors=["EMAIL ALREADY EXISTS"],
        failed_with_transient_error=False,
        error_kind=ErrorKind.PERMANENT,
    )
    with patch(REGISTER, return_value=refused):
        result = _add(pro, Pro.Engagement.MENTOR)

    assert result.errors == ["EMAIL ALREADY EXISTS"]
    pro.refresh_from_db()
    assert pro.engagements == []
    assert mail.outbox == []


def test_add_pro_engagement_makes_her_a_training_ambassador(
    pro, higher_ed_school, higher_ed_formation
):
    form = ProTrainingAmbassadorForm(
        data={"school_id": str(higher_ed_school.id), "formation_id": str(higher_ed_formation.pk)}
    )
    assert form.is_valid()

    _add(pro, Pro.Engagement.TRAINING_AMBASSADOR, training_ambassador_form=form)

    pro.refresh_from_db()
    assert pro.engagements == ["training_ambassador"]
    assert pro.training_experiences.get().school == higher_ed_school
    assert len(_sent_to("training@example.com")) == 1


# ------------------- workshop -------------------


def test_add_pro_engagement_forwards_one_more_workshop_request(pro):
    _with_engagements(pro, "workshops")
    with patch(NOTIFY_WORKSHOP) as notify:
        AddProEngagement(
            pro=pro,
            engagement=Pro.Engagement.WORKSHOPS,
            workshop_request_form=_workshop_request_form(),
        )

    pro.refresh_from_db()
    assert pro.engagements == ["workshops"]
    assert list(pro.workshop_requests.values_list("type", flat=True)) == ["future_of_tech"]
    assert notify.delay.call_args.kwargs["structure_uai"] == "0750001A"


@pytest.mark.parametrize(
    "job_title,profile",
    [
        ("Enseignante", ("school", "Lycée Voltaire", "Enseignante")),
        (
            "Autre mission au sein d'un établissement",
            ("school", "Lycée Voltaire", "Chercheuse"),
        ),
        ("DRANE / DAN / IAN", ("", "Inria", "Chercheuse")),
        ("parent d'élèves", ("", "Inria", "Chercheuse")),
    ],
)
def test_add_pro_engagement_takes_the_workshop_school_for_hers_when_she_works_there(
    pro, job_title, profile
):
    _add(
        pro,
        Pro.Engagement.WORKSHOPS,
        workshop_request_form=_workshop_request_form(job_title=job_title),
    )

    pro.refresh_from_db()
    assert (pro.structure_type, pro.structure_name, pro.job_title) == profile
    assert pro.postal_code == "75001"
