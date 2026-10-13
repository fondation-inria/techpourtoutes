import re
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import quote

import pytest
from django.core import mail
from django.urls import reverse
from waffle.testutils import override_switch

from techpourtoutes.models import Pro
from techpourtoutes.utils.funnel import FunnelSession

FUNNEL_URL = "/coalition/inscription/"
NEW_FUNNEL_URL = "/coalition/inscription/new/"

_EMAIL = {"email": "hedy@example.com"}
_IDENTITY = {
    "civility": "Madame",
    "first_name": "Hedy",
    "last_name": "Lamarr",
    "manifeste_accepted": "on",
    "terms_accepted": "on",
}
_ADDITIONAL_INFORMATION = {
    "structure_type": "company",
    "structure_name": "Inria",
    "job_title": "Chercheuse",
    "phone": "0612345678",
    "postal_code": "75011",
}
_WORKSHOP_REQUEST = {
    "workshop-job_title": "Enseignante",
    "workshop-structure_uai": "0750001A",
    "workshop-school_label": "Lycée Voltaire",
    "workshop-postal_code": "75005",
    "workshop-ateliers": ["future_of_tech"],
}

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def new_pro_features():
    with override_switch("new_pro_features", active=True):
        yield


@pytest.fixture(autouse=True)
def locmem_email(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


# Celery runs eagerly: a pro created with a workshop request would otherwise call n8n for real.
@pytest.fixture(autouse=True)
def notify_workshop_request():
    with patch(
        "techpourtoutes.services.pro.pro_engagement_mixin.notify_workshop_request_task"
    ) as task:
        yield task


def _funnel(client):
    return FunnelSession(SimpleNamespace(session=client.session), "pro_inscription_funnel")


# Starts the funnel midway, as if she had already answered `steps`.
def _seed_funnel(client, *, current, values=None, **steps):
    session = client.session
    funnel = FunnelSession(SimpleNamespace(session=session), "pro_inscription_funnel")
    funnel.update(**(values or {}))
    for step, data in steps.items():
        funnel.save_step(step, data)
    funnel.current_step = current
    session.save()


def _seed_until_engagements(client, *engagements, current, **steps):
    _seed_funnel(
        client,
        current=current,
        email=_EMAIL,
        identity=_IDENTITY,
        engagements={"engagements": list(engagements)},
        **steps,
    )


def _post_step(client, step, data=None):
    return client.post(FUNNEL_URL, {"action": step, **(data or {})})


def _checked_engagements(response):
    return re.findall(r'value="(\w+)"[^>]*\bchecked\b', response.content.decode())


# ------------------- feature switch -------------------


@pytest.mark.parametrize("url", [FUNNEL_URL, NEW_FUNNEL_URL])
def test_the_funnel_does_not_exist_while_the_switch_is_off(client, url):
    with override_switch("new_pro_features", active=False):
        assert client.get(url).status_code == 404


# ------------------- entering -------------------


def test_new_pro_inscription_funnel_redirects_to_the_funnel(client):
    response = client.get(NEW_FUNNEL_URL)
    assert response.status_code == 302
    assert response["Location"] == FUNNEL_URL


def test_new_pro_inscription_funnel_starts_over(client):
    _seed_funnel(client, current="identity", email=_EMAIL)
    client.get(NEW_FUNNEL_URL)
    assert _funnel(client).current_step is None
    assert "email" not in _funnel(client).answers


def test_new_pro_inscription_funnel_redirects_authenticated_user_to_account(client, pro):
    client.force_login(pro)
    response = client.get(NEW_FUNNEL_URL)
    assert response["Location"] == reverse("show_account")


def test_get_renders_the_email_step_of_a_fresh_funnel(client):
    response = client.get(FUNNEL_URL)
    assert response.status_code == 200
    assert response.context["step"] == "email"


# ------------------- email and identity -------------------


def test_email_step_advances_to_identity(client):
    response = _post_step(client, "email", _EMAIL)
    assert response.context["step"] == "identity"


def test_existing_email_redirects_to_login(client, pro):
    response = _post_step(client, "email", {"email": pro.email})
    assert response["HX-Redirect"].startswith(reverse("login_request"))
    assert f"back={quote(reverse('coalition_home'), safe='')}" in response["HX-Redirect"]


def test_identity_step_requires_the_manifeste(client):
    _seed_funnel(client, current="identity", email=_EMAIL)
    response = _post_step(client, "identity", {**_IDENTITY, "manifeste_accepted": ""})
    assert response.context["step"] == "identity"
    assert "identity" not in _funnel(client).answered


def test_identity_step_advances_to_engagements(client):
    _seed_funnel(client, current="identity", email=_EMAIL)
    response = _post_step(client, "identity", _IDENTITY)
    assert response.context["step"] == "engagements"


# ------------------- engagements -------------------


def test_an_engagement_coming_from_its_page_is_checked_beforehand(client):
    client.get(f"{NEW_FUNNEL_URL}?engagement=sponsor")
    _seed_funnel(client, current="engagements", email=_EMAIL, identity=_IDENTITY)
    response = client.get(FUNNEL_URL)
    assert _checked_engagements(response) == ["sponsor"]


def test_an_unknown_engagement_checks_nothing(client):
    client.get(f"{NEW_FUNNEL_URL}?engagement=nope")
    assert _funnel(client).answers["preselected_engagement"] == ""


def test_the_engagements_she_chose_win_over_the_one_checked_beforehand(client):
    _seed_funnel(
        client,
        current="engagements",
        values={"preselected_engagement": "sponsor"},
        email=_EMAIL,
        identity=_IDENTITY,
        engagements={"engagements": ["mentor"]},
    )
    response = client.get(FUNNEL_URL)
    assert _checked_engagements(response) == ["mentor"]


def test_engagements_step_keeps_every_engagement_checked(client):
    _seed_funnel(client, current="engagements", email=_EMAIL, identity=_IDENTITY)
    _post_step(client, "engagements", {"engagements": ["mentor", "sponsor"]})
    assert _funnel(client).answers["engagements"] == ["mentor", "sponsor"]


def test_engagements_step_requires_the_message_of_another_engagement(client):
    _seed_funnel(client, current="engagements", email=_EMAIL, identity=_IDENTITY)
    response = _post_step(client, "engagements", {"engagements": ["other"], "message": ""})
    assert response.context["step"] == "engagements"
    assert "engagements" not in _funnel(client).answered


def test_engagements_step_requires_an_engagement(client):
    _seed_funnel(client, current="engagements", email=_EMAIL, identity=_IDENTITY)
    response = _post_step(client, "engagements", {})
    assert response.context["step"] == "engagements"


@pytest.mark.parametrize(
    "engagements,step",
    [
        (["training_ambassador"], "training_ambassador"),
        (["workshops"], "workshop_request"),
        (["mentor"], "additional_information"),
        (["events"], "additional_information"),
        (["other"], "additional_information"),
        (["workshops", "sponsor"], "workshop_request"),
        (["workshops", "events"], "workshop_request"),
    ],
)
def test_engagements_step_leads_to_the_screen_they_call_for(client, engagements, step):
    _seed_funnel(client, current="engagements", email=_EMAIL, identity=_IDENTITY)
    response = _post_step(
        client, "engagements", {"engagements": engagements, "message": "Je veux aider."}
    )
    assert response.context["step"] == step


def test_several_engagements_go_through_every_screen_they_call_for(
    client, higher_ed_school, higher_ed_formation
):
    _seed_until_engagements(client, "training_ambassador", "mentor", current="training_ambassador")
    response = _post_step(
        client,
        "training_ambassador",
        {"school_id": str(higher_ed_school.id), "formation_id": str(higher_ed_formation.pk)},
    )
    assert response.context["step"] == "additional_information"


def test_only_the_last_screen_joins_the_coalition(client):
    _seed_until_engagements(client, "workshops", "sponsor", current="workshop_request")
    response = client.get(FUNNEL_URL)
    assert "Rejoindre la coalition" not in response.content.decode()

    response = _post_step(client, "workshop_request", _WORKSHOP_REQUEST)
    assert "Rejoindre la coalition" in response.content.decode()


@pytest.mark.parametrize(
    "engagements,step",
    [
        (["workshops", "events"], "workshop_request"),
        (["training_ambassador", "events"], "training_ambassador"),
    ],
)
def test_events_add_no_screen_to_the_one_of_an_engagement(client, engagements, step):
    _seed_until_engagements(client, *engagements, current=step)
    response = client.get(FUNNEL_URL)
    assert "Rejoindre la coalition" in response.content.decode()


def _field(response, name):
    return re.search(rf'<(input|button)[^>]*id="id_{name}"[^>]*>', response).group()


def test_the_last_screen_hides_the_school_and_job_given_for_the_workshop(client):
    _seed_until_engagements(client, "workshops", "sponsor", current="workshop_request")

    response = _post_step(client, "workshop_request", _WORKSHOP_REQUEST).content.decode()

    for name in ("job_title", "structure_name", "structure_type"):
        assert f'id="id_{name}"' not in response
    assert 'value="75005"' in _field(response, "postal_code")


def test_the_last_screen_asks_the_job_of_another_mission_at_the_school(client):
    _seed_until_engagements(client, "workshops", "sponsor", current="workshop_request")

    response = _post_step(
        client,
        "workshop_request",
        {**_WORKSHOP_REQUEST, "workshop-job_title": "Autre mission au sein d'un établissement"},
    ).content.decode()

    assert 'value=""' in _field(response, "job_title")
    for name in ("structure_name", "structure_type"):
        assert f'id="id_{name}"' not in response


def test_the_job_of_another_mission_is_saved_with_the_workshop_school(client):
    _seed_until_engagements(
        client,
        "workshops",
        "sponsor",
        current="additional_information",
        workshop_request={
            **_WORKSHOP_REQUEST,
            "workshop-job_title": "Autre mission au sein d'un établissement",
        },
    )

    _post_step(
        client, "additional_information", {**_ADDITIONAL_INFORMATION, "job_title": "Infirmière"}
    )

    pro = Pro.objects.get(email="hedy@example.com")
    assert (pro.structure_type, pro.structure_name, pro.job_title) == (
        "school",
        "Lycée Voltaire",
        "Infirmière",
    )


@pytest.mark.parametrize(
    "job_title",
    ["DRANE / DAN / IAN", "parent d'élèves", "je ne travaille pas dans un établissement"],
)
def test_the_last_screen_asks_for_her_own_structure_when_she_works_elsewhere(client, job_title):
    _seed_until_engagements(client, "workshops", "sponsor", current="workshop_request")

    response = _post_step(
        client, "workshop_request", {**_WORKSHOP_REQUEST, "workshop-job_title": job_title}
    ).content.decode()

    for name in ("job_title", "structure_name", "structure_type"):
        assert "disabled" not in _field(response, name)


def test_the_structure_she_gives_is_saved_when_she_works_elsewhere(client):
    _seed_until_engagements(
        client,
        "workshops",
        "sponsor",
        current="additional_information",
        workshop_request={**_WORKSHOP_REQUEST, "workshop-job_title": "DRANE / DAN / IAN"},
    )

    _post_step(client, "additional_information", _ADDITIONAL_INFORMATION)

    pro = Pro.objects.get(email="hedy@example.com")
    assert (pro.structure_type, pro.structure_name, pro.job_title) == (
        "company",
        "Inria",
        "Chercheuse",
    )


def test_the_job_given_for_the_workshop_is_the_one_saved(client):
    _seed_until_engagements(
        client,
        "workshops",
        "sponsor",
        current="additional_information",
        workshop_request=_WORKSHOP_REQUEST,
    )

    _post_step(
        client, "additional_information", {**_ADDITIONAL_INFORMATION, "job_title": "Chercheuse"}
    )

    pro = Pro.objects.get(email="hedy@example.com")
    assert (pro.structure_type, pro.structure_name, pro.job_title) == (
        "school",
        "Lycée Voltaire",
        "Enseignante",
    )


def test_the_job_is_free_again_once_the_workshop_is_no_longer_wanted(client):
    _seed_until_engagements(
        client, "sponsor", current="additional_information", workshop_request=_WORKSHOP_REQUEST
    )

    _post_step(
        client, "additional_information", {**_ADDITIONAL_INFORMATION, "job_title": "Chercheuse"}
    )

    assert Pro.objects.get(email="hedy@example.com").job_title == "Chercheuse"


def test_back_from_engagements_returns_to_identity(client):
    _seed_funnel(client, current="engagements", email=_EMAIL, identity=_IDENTITY)
    response = client.post(FUNNEL_URL, {"action": "back"})
    assert response.context["step"] == "identity"


def test_a_screen_sent_without_an_earlier_one_goes_back_to_the_first_missing(client):
    _seed_funnel(client, current="identity", email=_EMAIL)
    response = _post_step(client, "additional_information", _ADDITIONAL_INFORMATION)
    assert response.context["step"] == "identity"
    assert b"Reprenez" in response.content


# ------------------- account creation -------------------


def test_the_last_screen_creates_the_pro_and_shows_the_code_screen(client):
    _seed_until_engagements(client, "sponsor", current="additional_information")

    response = _post_step(client, "additional_information", _ADDITIONAL_INFORMATION)

    assert response.context["step"] == "code"
    assert _funnel(client).answers == {}
    pro = Pro.objects.get(email="hedy@example.com")
    assert pro.engagements == ["sponsor"]
    assert pro.structure_name == "Inria"


def test_the_last_screen_sends_the_welcome_mail_with_the_login_code(client):
    _seed_until_engagements(client, "sponsor", current="additional_information")

    _post_step(client, "additional_information", _ADDITIONAL_INFORMATION)

    welcome = next(m for m in mail.outbox if m.to == ["hedy@example.com"])
    code = re.search(r"\b(\d{6})\b", welcome.body).group(1)
    assert Pro.objects.get(email="hedy@example.com").consume_login_code(code)


def test_the_message_of_another_engagement_reaches_the_team(client, settings):
    settings.COALITION_OTHER_ENGAGEMENT_RECIPIENTS = ["agir@example.com"]
    _seed_funnel(
        client,
        current="additional_information",
        email=_EMAIL,
        identity=_IDENTITY,
        engagements={"engagements": ["other"], "message": "Je veux aider autrement."},
    )

    _post_step(client, "additional_information", _ADDITIONAL_INFORMATION)

    [relayed] = [m for m in mail.outbox if m.to == ["agir@example.com"]]
    assert "Je veux aider autrement." in relayed.body


def test_a_refused_account_creation_stays_on_the_last_screen_with_the_error(client):
    _seed_until_engagements(client, "mentor", current="additional_information")
    refused = MagicMock(failure=True, errors=["EMAIL ALREADY EXISTS"])

    with patch("techpourtoutes.views.pro.inscription_views.CreatePro", return_value=refused):
        response = _post_step(client, "additional_information", _ADDITIONAL_INFORMATION)

    assert response.context["step"] == "additional_information"
    assert b"EMAIL ALREADY EXISTS" in response.content


def test_the_code_screen_remembers_she_only_wants_to_propose_events(client):
    _seed_until_engagements(client, "events", current="additional_information")
    response = _post_step(client, "additional_information", _ADDITIONAL_INFORMATION)
    assert re.search(r'name="events_only" value="1"', response.content.decode())


def test_the_code_screen_forgets_events_proposed_alongside_another_engagement(client):
    _seed_until_engagements(client, "events", "sponsor", current="additional_information")
    response = _post_step(client, "additional_information", _ADDITIONAL_INFORMATION)
    assert re.search(r'name="events_only" value=""', response.content.decode())


# ------------------- login code -------------------


def _code_for(pro):
    return pro.issue_login_code()


def test_a_valid_code_logs_in_and_shows_the_account_with_the_welcome_modal(client, pro):
    response = client.post(
        FUNNEL_URL, {"action": "code", "email": pro.email, "code": _code_for(pro)}
    )

    assert response["HX-Redirect"] == reverse("show_account")
    assert client.session.get("_auth_user_id") == str(pro.pk)
    account = client.get(reverse("show_account"))
    assert "Bienvenue dans la coalition" in account.content.decode()


def test_a_valid_code_leads_to_her_events_when_she_only_wants_to_propose_some(client, pro):
    response = client.post(
        FUNNEL_URL,
        {"action": "code", "email": pro.email, "code": _code_for(pro), "events_only": "1"},
    )

    assert response["HX-Redirect"] == reverse("index_pro_events")
    events = client.get(reverse("index_pro_events"))
    assert "Bienvenue dans la coalition" in events.content.decode()


def test_an_invalid_code_stays_on_the_code_screen(client, pro):
    response = client.post(FUNNEL_URL, {"action": "code", "email": pro.email, "code": "000000"})
    assert response.context["step"] == "code"
    assert b"Code invalide" in response.content
    assert "_auth_user_id" not in client.session


def test_resend_sends_a_new_login_code(client, pro):
    response = client.post(FUNNEL_URL, {"action": "resend", "email": pro.email})
    assert response.context["step"] == "code"
    assert [m.to for m in mail.outbox] == [[pro.email]]
