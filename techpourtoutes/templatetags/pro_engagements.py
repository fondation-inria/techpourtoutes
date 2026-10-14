"""What an engagement button does for whoever sees it.
No action, no button: a beneficiary, or a pro who may not take the engagement on. `next` is
where a failed addition sends her back, with its message; success leads to her account.
"""

from django import template

from ..services.pro.check_pro_engagement_eligibility import CheckProEngagementEligibility
from ..utils.pro_engagement_screens import screen_for

register = template.Library()


@register.simple_tag
def pro_engagement_action(user, engagement):
    """ "sign_up", "complete", "add" — or "" when there is no button to show."""
    if not user.is_authenticated:
        return "sign_up"
    if not hasattr(user, "pro"):
        return ""
    pro = user.pro
    if CheckProEngagementEligibility(pro=pro, engagement=engagement).failure:
        return ""
    return "complete" if screen_for(pro, engagement) else "add"
