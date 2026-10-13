import pytest
from django.contrib.auth.models import AnonymousUser

from techpourtoutes.models import Pro, User
from techpourtoutes.templatetags.pro_engagements import pro_engagement_action

pytestmark = pytest.mark.django_db


# As `request.user` comes: the user, whose `pro` is looked up.
def _signed_in(user):
    user.save()
    return User.objects.get(pk=user.pk)


def test_a_visitor_signs_up_with_the_engagement():
    assert pro_engagement_action(AnonymousUser(), "sponsor") == "sign_up"


def test_a_beneficiary_gets_no_engagement_button(beneficiary):
    assert pro_engagement_action(_signed_in(beneficiary), "sponsor") == ""


def test_a_pro_gets_no_button_for_an_engagement_she_may_not_take_on(pro):
    pro.engagements = ["sponsor"]
    assert pro_engagement_action(_signed_in(pro), "sponsor") == ""


@pytest.mark.parametrize("engagement", ["sponsor", "training_ambassador", "workshops"])
def test_a_pro_completes_what_the_engagement_still_needs(pro, engagement):
    assert pro_engagement_action(_signed_in(pro), engagement) == "complete"


def test_a_pro_adds_at_once_what_needs_nothing_more(pro):
    pro.structure_type = Pro.StructureType.COMPANY
    assert pro_engagement_action(_signed_in(pro), "sponsor") == "add"
