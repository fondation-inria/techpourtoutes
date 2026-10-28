import re
from unittest.mock import MagicMock, patch

import pytest
from django.core import mail

from techpourtoutes.forms import ProTrainingAmbassadorForm, ProWorkshopRequestForm
from techpourtoutes.models import Pro, WorkshopRequest
from techpourtoutes.services.base import ErrorKind
from techpourtoutes.services.pro.create_pro import CreatePro

REGISTER = "techpourtoutes.services.pro.create_mentor.RegisterUserOnJobirl"
NOTIFY_WORKSHOP = "techpourtoutes.services.pro.pro_engagement_mixin.notify_workshop_request_task"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def mail_recipients(settings):
    settings.COALITION_WORK_AMBASSADOR_RECIPIENTS = ["company@example.com"]
    settings.COALITION_TRAINING_AMBASSADOR_RECIPIENTS = ["training@example.com"]


def _identity(**overrides):
    return {
        "email": "hedy@example.com",
        "civility": "Madame",
        "first_name": "Hedy",
        "last_name": "Lamarr",
        "newsletter_consent": True,
        **overrides,
    }


def _engagements(*engagements, message=""):
    return {"engagements": list(engagements), "message": message}


def _additional_information(**overrides):
    return {
        "structure_type": Pro.StructureType.COMPANY,
        "structure_name": "Inria",
        "job_title": "Chercheuse",
        "phone": "+33612345678",
        "postal_code": "75011",
        **overrides,
    }


def _workshop_request_form(**overrides):
    answers = {
        "job_title": "Enseignante",
        "structure_uai": "0750001A",
        "school_label": "Lycée Voltaire",
        "postal_code": "75005",
        "ateliers": ["future_of_tech", "future_of_ia"],
        "remark": "Plutôt en mai",
        **overrides,
    }
    form = ProWorkshopRequestForm(data={f"workshop-{name}": v for name, v in answers.items()})
    assert form.is_valid()
    return form


def _training_ambassador_form(school, formation, **overrides):
    form = ProTrainingAmbassadorForm(
        data={"school_id": str(school.id), "formation_id": str(formation.pk), **overrides}
    )
    assert form.is_valid()
    return form


def _create(*engagements, message="", **kwargs):
    with patch(NOTIFY_WORKSHOP):
        return CreatePro(
            identity=_identity(), engagements=_engagements(*engagements, message=message), **kwargs
        )


def _sent_to(recipient):
    return [message for message in mail.outbox if recipient in message.to]


# ------------------- the pro -------------------


def test_create_pro_saves_her_identity_and_information():
    result = _create("sponsor", additional_information=_additional_information())

    assert result.success
    pro = Pro.objects.get(email="hedy@example.com")
    assert (pro.civility, pro.first_name, pro.last_name) == ("Madame", "Hedy", "Lamarr")
    assert pro.brevo_sync_enabled is True
    assert pro.structure_type == "company"
    assert pro.structure_name == "Inria"
    assert pro.job_title == "Chercheuse"
    assert pro.postal_code == "75011"
    assert pro.phone == "+33612345678"
    assert not pro.has_usable_password()


def test_create_pro_stores_neither_events_nor_other_as_engagements():
    _create("sponsor", "events", "other", additional_information=_additional_information())

    assert Pro.objects.get(email="hedy@example.com").engagements == ["sponsor"]


# ------------------- training ambassador -------------------


def test_create_pro_saves_the_training_of_a_training_ambassador(
    higher_ed_school, higher_ed_formation
):
    _create(
        "training_ambassador",
        training_ambassador_form=_training_ambassador_form(
            higher_ed_school, higher_ed_formation, phone="0612345678"
        ),
    )

    pro = Pro.objects.get(email="hedy@example.com")
    assert pro.engagements == ["training_ambassador"]
    assert pro.phone == "+33612345678"
    assert pro.training_experiences.get().school == higher_ed_school


def test_create_pro_takes_the_school_of_a_training_ambassador_for_her_structure(
    higher_ed_school, higher_ed_formation
):
    _create(
        "training_ambassador",
        training_ambassador_form=_training_ambassador_form(higher_ed_school, higher_ed_formation),
    )

    pro = Pro.objects.get(email="hedy@example.com")
    assert (pro.structure_type, pro.structure_name) == ("higher_ed", "Université Paris-Saclay")


def test_create_pro_tells_the_team_and_the_training_ambassador(
    higher_ed_school, higher_ed_formation
):
    _create(
        "training_ambassador",
        training_ambassador_form=_training_ambassador_form(higher_ed_school, higher_ed_formation),
    )

    assert len(_sent_to("training@example.com")) == 1
    subjects = [message.subject for message in _sent_to("hedy@example.com")]
    assert "Une dernière étape pour devenir ambassadrice étudiante" in subjects


# ------------------- workshop -------------------


def test_create_pro_records_one_workshop_request_per_workshop():
    with patch(NOTIFY_WORKSHOP) as notify:
        CreatePro(
            identity=_identity(),
            engagements=_engagements("workshops"),
            workshop_request_form=_workshop_request_form(),
        )

    pro = Pro.objects.get(email="hedy@example.com")
    assert pro.structure_type == "school"
    assert pro.structure_name == "Lycée Voltaire"
    assert pro.job_title == "Enseignante"
    assert pro.postal_code == ""
    assert sorted(pro.workshop_requests.values_list("type", flat=True)) == [
        "future_of_ia",
        "future_of_tech",
    ]
    assert set(WorkshopRequest.objects.values_list("remark", flat=True)) == {"Plutôt en mai"}
    notify.delay.assert_called_once_with(
        pro_pk=str(pro.pk),
        ateliers=["future_of_tech", "future_of_ia"],
        remark="Plutôt en mai",
        structure_uai="0750001A",
    )


@pytest.mark.parametrize(
    "job_title",
    ["DRANE / DAN / IAN", "parent d'élèves", "je ne travaille pas dans un établissement"],
)
def test_create_pro_does_not_take_the_workshop_school_for_hers_when_she_works_elsewhere(
    job_title,
):
    with patch(NOTIFY_WORKSHOP) as notify:
        CreatePro(
            identity=_identity(),
            engagements=_engagements("workshops"),
            workshop_request_form=_workshop_request_form(job_title=job_title),
        )

    pro = Pro.objects.get(email="hedy@example.com")
    assert (pro.structure_type, pro.structure_name, pro.job_title, pro.postal_code) == (
        "",
        "",
        "",
        "",
    )
    assert pro.workshop_requests.count() == 2
    assert notify.delay.call_args.kwargs["structure_uai"] == "0750001A"


def test_create_pro_leaves_the_job_of_another_mission_at_the_school_blank():
    _create(
        "workshops",
        workshop_request_form=_workshop_request_form(
            job_title="Autre mission au sein d'un établissement"
        ),
    )

    pro = Pro.objects.get(email="hedy@example.com")
    assert (pro.structure_type, pro.structure_name, pro.job_title) == (
        "school",
        "Lycée Voltaire",
        "",
    )


def test_create_pro_keeps_the_additional_information_over_the_workshop_ones():
    _create(
        "workshops",
        "sponsor",
        workshop_request_form=_workshop_request_form(),
        additional_information=_additional_information(),
    )

    pro = Pro.objects.get(email="hedy@example.com")
    assert pro.job_title == "Chercheuse"
    assert pro.structure_name == "Inria"


# ------------------- mails -------------------


def test_create_pro_welcomes_her_with_a_login_code():
    _create("sponsor", additional_information=_additional_information())

    welcome = next(m for m in _sent_to("hedy@example.com") if "Bienvenue" in m.subject)
    code = re.search(r"\b(\d{6})\b", welcome.body).group(1)
    assert Pro.objects.get(email="hedy@example.com").consume_login_code(code)


def test_create_pro_tells_the_team_about_a_structure_to_mobilize():
    _create("mobilize_structure", additional_information=_additional_information())

    assert len(_sent_to("company@example.com")) == 1


def test_create_pro_relays_the_message_of_another_engagement():
    _create(
        "other",
        message="Je veux aider autrement.",
        additional_information=_additional_information(),
    )

    [relayed] = _sent_to("company@example.com")
    assert "Je veux aider autrement." in relayed.body


def test_create_pro_relays_the_message_of_another_engagement_to_its_team_only():
    _create(
        "other",
        "mobilize_structure",
        message="Je veux aider autrement.",
        additional_information=_additional_information(),
    )

    [notified] = [m for m in _sent_to("company@example.com") if "sa structure" in m.subject]
    assert "Je veux aider autrement." not in notified.body


def test_create_pro_relays_nothing_without_another_engagement():
    _create("sponsor", additional_information=_additional_information())

    assert _sent_to("company@example.com") == []


# ------------------- mentor -------------------


def test_create_pro_registers_a_mentor_on_jobirl():
    registered = MagicMock(success=True, failure=False, user_id=287565, token="tpt_abc")
    with patch(REGISTER, return_value=registered):
        result = _create("mentor", additional_information=_additional_information())

    assert result.success
    pro = Pro.objects.get(email="hedy@example.com")
    assert pro.engagements == ["mentor"]
    assert pro.jobirl_user_id == 287565


@pytest.mark.django_db(transaction=True)
def test_create_pro_saves_nothing_when_jobirl_refuses_the_mentor():
    refused = MagicMock(
        success=False,
        failure=True,
        errors=["EMAIL ALREADY EXISTS"],
        failed_with_transient_error=False,
        error_kind=ErrorKind.PERMANENT,
    )
    with patch(REGISTER, return_value=refused):
        result = _create("mentor", additional_information=_additional_information())

    assert result.failure
    assert result.errors == ["EMAIL ALREADY EXISTS"]
    assert not Pro.objects.filter(email="hedy@example.com").exists()
    assert mail.outbox == []
