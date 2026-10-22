import pytest
from django.contrib.auth.models import AnonymousUser

from techpourtoutes.forms.pro_inscription import ProEngagementsForm
from techpourtoutes.models import Pro, User
from techpourtoutes.templatetags.pro_engagements import (
    BENEFICIARY_REFUSAL_REASON,
    pro_engagement_action,
)

pytestmark = pytest.mark.django_db


# As `request.user` comes: the user, whose `pro` is looked up.
def _signed_in(user):
    user.save()
    return User.objects.get(pk=user.pk)


@pytest.mark.parametrize("engagement", ["sponsor", "training_ambassador", "mobilize_structure"])
def test_a_visitor_signs_up_with_the_engagement(engagement):
    assert pro_engagement_action(AnonymousUser(), engagement) == ("sign_up", "")


@pytest.mark.parametrize("engagement", ["mentor", "sponsor", "training_ambassador", "workshops"])
def test_a_beneficiary_sees_the_engagement_disabled(beneficiary, engagement):
    assert pro_engagement_action(_signed_in(beneficiary), engagement) == (
        "disabled",
        BENEFICIARY_REFUSAL_REASON,
    )


def test_a_beneficiary_gets_no_button_to_mobilize_a_structure(beneficiary):
    assert pro_engagement_action(_signed_in(beneficiary), "mobilize_structure") == ("", "")


def test_a_pro_gets_no_button_to_mobilize_a_structure(pro):
    assert pro_engagement_action(_signed_in(pro), "mobilize_structure") == ("", "")


@pytest.mark.parametrize("engagement", ["mentor", "sponsor", "workshops"])
def test_a_training_ambassador_sees_the_other_engagements_disabled(pro, engagement):
    pro.engagements = ["training_ambassador"]
    assert pro_engagement_action(_signed_in(pro), engagement) == (
        "disabled",
        ProEngagementsForm.student_only_reason,
    )


def test_a_training_ambassador_gets_no_button_for_her_own_engagement(pro):
    pro.engagements = ["training_ambassador"]
    assert pro_engagement_action(_signed_in(pro), "training_ambassador") == ("", "")


def test_a_pro_engaged_otherwise_sees_training_ambassador_disabled(pro):
    pro.engagements = ["mentor"]
    assert pro_engagement_action(_signed_in(pro), "training_ambassador") == (
        "disabled",
        ProEngagementsForm.training_ambassador_apart_reason,
    )


def test_a_mentor_reaches_her_mentoring_space(pro):
    pro.engagements = ["mentor"]
    assert pro_engagement_action(_signed_in(pro), "mentor") == ("mentoring_space", "")


def test_a_work_ambassador_gets_no_button_for_her_own_engagement(pro):
    pro.engagements = ["work_ambassador"]
    assert pro_engagement_action(_signed_in(pro), "work_ambassador") == ("", "")


@pytest.mark.parametrize(("engagement", "action"), [("sponsor", "add"), ("workshops", "complete")])
def test_a_pro_may_take_on_again_a_sponsorship_or_a_workshop(pro, engagement, action):
    pro.structure_type = Pro.StructureType.COMPANY
    pro.engagements = [engagement]
    assert pro_engagement_action(_signed_in(pro), engagement) == (action, "")


@pytest.mark.parametrize("engagement", ["sponsor", "training_ambassador", "workshops"])
def test_a_pro_completes_what_the_engagement_still_needs(pro, engagement):
    assert pro_engagement_action(_signed_in(pro), engagement) == ("complete", "")


def test_a_pro_adds_at_once_what_needs_nothing_more(pro):
    pro.structure_type = Pro.StructureType.COMPANY
    assert pro_engagement_action(_signed_in(pro), "sponsor") == ("add", "")
