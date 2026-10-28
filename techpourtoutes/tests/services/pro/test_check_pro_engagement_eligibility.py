import pytest

from techpourtoutes.models import Pro
from techpourtoutes.services.pro.check_pro_engagement_eligibility import (
    CheckProEngagementEligibility,
)


@pytest.mark.parametrize(
    "engagements,engagement",
    [
        ([], "mentor"),
        ([], "training_ambassador"),
        (["sponsor"], "mentor"),
        (["workshops"], "workshops"),
        (["sponsor"], "sponsor"),
    ],
)
def test_check_pro_engagement_eligibility_lets_her_take_it_on(engagements, engagement):
    result = CheckProEngagementEligibility(pro=Pro(engagements=engagements), engagement=engagement)
    assert result.success
    assert result.refusal_reason is None


@pytest.mark.parametrize(
    "engagements,engagement,reason",
    [
        (["mentor"], "mentor", "déjà pris cet engagement"),
        (["training_ambassador"], "training_ambassador", "déjà pris cet engagement"),
        (["training_ambassador"], "mentor", "Si vous êtes étudiante"),
        (["training_ambassador"], "workshops", "Si vous êtes étudiante"),
        (["mentor"], "training_ambassador", "pas compatible"),
    ],
)
def test_check_pro_engagement_eligibility_says_why_she_may_not(engagements, engagement, reason):
    result = CheckProEngagementEligibility(pro=Pro(engagements=engagements), engagement=engagement)
    assert result.failure
    assert reason in result.refusal_reason
    assert result.errors == [str(result.refusal_reason)]
