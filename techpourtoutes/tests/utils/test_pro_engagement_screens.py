import pytest

from techpourtoutes.models import Pro
from techpourtoutes.utils.pro_engagement_screens import screen_for


@pytest.mark.parametrize(
    "engagement,screen",
    [
        ("training_ambassador", "training_ambassador"),
        ("workshops", "workshop_request"),
        ("sponsor", "sponsor"),
    ],
)
def test_an_engagement_with_its_own_screen_always_asks_for_it(pro, engagement, screen):
    pro.structure_type = Pro.StructureType.COMPANY
    assert screen_for(pro, engagement) == screen


def test_another_engagement_asks_what_her_profile_lacks(pro):
    assert screen_for(pro, "internships") == "additional_information"


def test_another_engagement_asks_nothing_of_a_complete_profile(pro):
    pro.structure_type = Pro.StructureType.COMPANY
    assert screen_for(pro, "internships") is None
