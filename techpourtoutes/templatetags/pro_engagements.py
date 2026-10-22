"""What an engagement button does for whoever sees it.
A pro who may not take the engagement on sees it disabled, with the reason; one who already
took it on gets no button, but for the ones she may give again and the mentors, sent to their
space. `next` is where a failed addition sends her back, with its message; success leads to her
account.
"""

from typing import NamedTuple

from django import template
from django.utils.translation import gettext_lazy as _

from ..models import Pro
from ..services.pro.check_pro_engagement_eligibility import CheckProEngagementEligibility
from ..utils.pro_engagement_screens import screen_for

register = template.Library()

BENEFICIARY_REFUSAL_REASON = _(
    "Cet engagement est réservé aux professionnelles. Tu es inscrite sur TechPourToutes en tant "
    "que lycéenne ou étudiante."
)

# Taken on again at will, unlike the others.
_REPEATABLE = (Pro.Engagement.SPONSOR, Pro.Engagement.WORKSHOPS)


class EngagementAction(NamedTuple):
    name: str
    refusal_reason: str = ""


_NO_BUTTON = EngagementAction("")


@register.simple_tag
def pro_engagement_action(user, engagement):
    """ "sign_up", "complete", "add", "mentoring_space", "disabled" with its `refusal_reason` —
    or "" when there is no button to show."""
    if not user.is_authenticated:
        return EngagementAction("sign_up")
    if engagement == Pro.Engagement.MOBILIZE_STRUCTURE:
        return _NO_BUTTON
    if not hasattr(user, "pro"):
        return EngagementAction("disabled", BENEFICIARY_REFUSAL_REASON)
    return _pro_engagement_action(user.pro, engagement)


@register.simple_tag
def beneficiary_refusal_reason():
    """For the buttons kept for pros that are no engagement, such as events or internships."""
    return BENEFICIARY_REFUSAL_REASON


def _pro_engagement_action(pro, engagement):
    if engagement in pro.engagements:
        return _already_taken_action(pro, engagement)
    eligibility = CheckProEngagementEligibility(pro=pro, engagement=engagement)
    if eligibility.failure:
        return EngagementAction("disabled", eligibility.refusal_reason)
    return _addition(pro, engagement)


def _already_taken_action(pro, engagement):
    if engagement == Pro.Engagement.MENTOR:
        return EngagementAction("mentoring_space")
    if engagement in _REPEATABLE:
        return _addition(pro, engagement)
    return _NO_BUTTON


def _addition(pro, engagement):
    return EngagementAction("complete" if screen_for(pro, engagement) else "add")
