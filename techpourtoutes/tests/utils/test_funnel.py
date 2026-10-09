from datetime import timedelta

import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.utils import timezone

from techpourtoutes.utils.funnel import FunnelSession, FunnelSteps

_STEPS = FunnelSteps(
    ("email", "identity", "study", "mentoring", "ambassador"),
    optional={"mentoring": "wants_mentor", "ambassador": "wants_ambassador"},
)


@pytest.fixture
def request_with_session():
    request = RequestFactory().get("/")
    SessionMiddleware(lambda request: None).process_request(request)
    return request


def _funnel(request):
    return FunnelSession(request, "test_funnel")


# ------------------- FunnelSteps -------------------


def test_active_leaves_out_the_optional_steps_not_wanted():
    assert _STEPS.active({"wants_ambassador": True}) == [
        "email",
        "identity",
        "study",
        "ambassador",
    ]


def test_first_is_the_first_step():
    assert _STEPS.first == "email"


def test_next_skips_an_optional_step_not_wanted():
    assert _STEPS.next("study", {"wants_ambassador": True}) == "ambassador"


def test_previous_skips_an_optional_step_not_wanted():
    assert _STEPS.previous("ambassador", {"wants_ambassador": True}) == "study"


def test_previous_of_the_first_step_stays_on_it():
    assert _STEPS.previous("email", {}) == "email"


def test_previous_of_an_unknown_step_falls_back_to_the_first():
    assert _STEPS.previous("nope", {}) == "email"


def test_an_optional_step_is_left_out_while_its_answer_is_false():
    assert "mentoring" not in _STEPS.active({"wants_mentor": False})


def test_last_depends_on_the_optional_steps_wanted():
    assert _STEPS.last({}) == "study"
    assert _STEPS.last({"wants_mentor": True}) == "mentoring"


def test_next_of_a_step_no_longer_active_is_the_active_one_following_it():
    assert _STEPS.next("mentoring", {"wants_ambassador": True}) == "ambassador"


def test_next_of_the_last_active_step_is_none():
    assert _STEPS.next("study", {}) is None
    assert _STEPS.next("mentoring", {}) is None


def test_missing_before_is_none_once_every_earlier_step_is_answered():
    assert _STEPS.missing_before("study", {"email", "identity"}, {}) is None


def test_missing_before_returns_the_first_earlier_step_not_answered():
    assert _STEPS.missing_before("study", {"email"}, {}) == "identity"
    assert _STEPS.missing_before("study", set(), {}) == "email"


def test_missing_before_the_first_step_is_none():
    assert _STEPS.missing_before("email", set(), {}) is None


def test_missing_before_only_requires_the_active_steps():
    answered = {"email", "identity", "study"}
    assert _STEPS.missing_before("ambassador", answered, {"wants_ambassador": True}) is None
    assert _STEPS.missing_before("ambassador", answered, {"wants_mentor": True}) == "mentoring"


def test_progress_leaves_the_first_step_without_a_bar():
    assert _STEPS.progress("email", {}) is None


def test_progress_keeps_a_share_for_the_success_screen():
    assert _STEPS.progress("identity", {}) == 33
    assert _STEPS.progress("study", {}) == 67


# ------------------- FunnelSession -------------------


def test_a_fresh_funnel_has_no_answers_nor_current_step(request_with_session):
    funnel = _funnel(request_with_session)
    assert funnel.answers == {}
    assert funnel.current_step is None


def test_answers_merge_the_values_and_every_step(request_with_session):
    funnel = _funnel(request_with_session)
    funnel.update(wants_mentor=True)
    funnel.save_step("email", {"email": "oceane@example.com"})
    funnel.save_step("identity", {"first_name": "Océane"})
    assert funnel.answers == {
        "wants_mentor": True,
        "email": "oceane@example.com",
        "first_name": "Océane",
    }


def test_save_step_replaces_the_previous_answers_of_that_step(request_with_session):
    funnel = _funnel(request_with_session)
    funnel.save_step("identity", {"first_name": "Océane", "newsletter_consent": "on"})
    funnel.save_step("identity", {"first_name": "Léa"})
    assert funnel.answers == {"first_name": "Léa"}


def test_save_step_ignores_the_control_fields(request_with_session):
    funnel = _funnel(request_with_session)
    funnel.save_step("email", {"email": "a@b.fr", "action": "email", "csrfmiddlewaretoken": "t"})
    assert funnel.answers == {"email": "a@b.fr"}


def test_answers_with_replaces_one_step_without_saving_it(request_with_session):
    funnel = _funnel(request_with_session)
    funnel.save_step("email", {"email": "a@b.fr"})
    funnel.save_step("identity", {"first_name": "Océane", "newsletter_consent": "on"})
    assert funnel.answers_with("identity", {"first_name": "Léa", "action": "identity"}) == {
        "email": "a@b.fr",
        "first_name": "Léa",
    }
    assert funnel.answers["first_name"] == "Océane"


def test_answered_lists_the_saved_steps(request_with_session):
    funnel = _funnel(request_with_session)
    funnel.update(wants_mentor=True)
    funnel.save_step("email", {"email": "a@b.fr"})
    funnel.save_step("identity", {"first_name": "Océane"})
    assert funnel.answered == {"email", "identity"}


def test_the_state_survives_into_the_next_request(request_with_session):
    _funnel(request_with_session).save_step("email", {"email": "a@b.fr"})
    _funnel(request_with_session).current_step = "identity"
    funnel = _funnel(request_with_session)
    assert funnel.answers == {"email": "a@b.fr"}
    assert funnel.current_step == "identity"


def test_clear_forgets_everything(request_with_session):
    funnel = _funnel(request_with_session)
    funnel.save_step("email", {"email": "a@b.fr"})
    funnel.current_step = "identity"
    funnel.clear()
    assert funnel.answers == {}
    assert funnel.current_step is None
    assert "test_funnel" not in request_with_session.session


def test_answers_older_than_an_hour_are_forgotten(request_with_session):
    funnel = _funnel(request_with_session)
    funnel.save_step("email", {"email": "a@b.fr"})
    funnel.current_step = "identity"
    state = request_with_session.session["test_funnel"]
    state["updated_at"] = (timezone.now() - timedelta(minutes=61)).isoformat()
    request_with_session.session["test_funnel"] = state
    assert funnel.answers == {}
    assert funnel.current_step is None
