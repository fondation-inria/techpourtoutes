"""What an engagement button does for whoever sees it.

    {% load pro_engagements %}
    {% pro_engagement_action request.user "mentor" as action %}
    {% url "create_pro_engagement" "mentor" as add_url %}
    {% url "new_pro_engagement" "mentor" as new_url %}
    {% if action == "add" %}
        {# Nothing left to give: the click itself adds the engagement. #}
        <c-patterns.form hx-post="{{ add_url }}?next={{ request.get_full_path|urlencode }}">
            <c-components.button type="submit" label="Devenir mentor" />
        </c-patterns.form>
    {% elif action %}
        {# "complete": the screen the engagement still calls for; "sign_up": the inscription. #}
        <c-components.button href="{{ new_url }}" label="Devenir mentor" />
    {% endif %}

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
