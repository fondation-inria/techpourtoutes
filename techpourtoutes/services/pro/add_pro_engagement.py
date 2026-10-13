from ...mailers import ProMailer
from ..base import BaseService
from .check_pro_engagement_eligibility import CheckProEngagementEligibility
from .pro_engagement_mixin import ProEngagementMixin


class AddProEngagement(ProEngagementMixin, BaseService):
    """Adds one more engagement to a pro who already has an account, along with what she
    told about it — unless she is not eligible for it."""

    origin = "Ajout d'engagement pro"

    def perform(
        self,
        *,
        pro,
        engagement,
        training_ambassador_form=None,
        workshop_request_form=None,
        additional_information=None,
    ):
        eligibility = CheckProEngagementEligibility(pro=pro, engagement=engagement)
        if eligibility.failure:
            self.fail_with_errors(eligibility)
        self.pro = pro
        self.pro.add_engagement(engagement)
        self._save_pro_with(
            training_ambassador_form, workshop_request_form, additional_information
        )

        ProMailer.engagement_added(pro=self.pro)
        self._notify_about_engagements([engagement])
