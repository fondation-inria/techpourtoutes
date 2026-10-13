from ...forms.pro_inscription import EVENTS, OTHER
from ...mailers import ConsortiumMailer, ProMailer
from ...models import Pro
from ..base import BaseService
from .pro_engagement_mixin import ProEngagementMixin


class CreatePro(ProEngagementMixin, BaseService):
    """Creates the pro who went through the inscription funnel, along with what each of her
    engagements calls for."""

    origin = "Funnel d'inscription pro"

    def perform(
        self,
        *,
        identity,
        engagements,
        training_ambassador_form=None,
        workshop_request_form=None,
        additional_information=None,
    ):
        self.chosen = engagements["engagements"]
        # Working, unless her answers say otherwise.
        self.pro = Pro(
            username=identity["email"],
            email=identity["email"],
            professional_situation=Pro.ProfessionalSituation.WORKING,
        )
        self._apply_identity(identity)
        self._save_pro_with(
            training_ambassador_form, workshop_request_form, additional_information
        )

        ProMailer.welcome(pro=self.pro, code=self.pro.issue_login_code())
        if OTHER in self.chosen:
            ConsortiumMailer.other_engagement_requested(
                pro=self.pro, message=engagements["message"]
            )
        self._notify_about_engagements(self.pro.engagements)

    def _apply_identity(self, identity):
        self.pro.civility = identity["civility"]
        self.pro.first_name = identity["first_name"]
        self.pro.last_name = identity["last_name"]
        self.pro.brevo_sync_enabled = identity["newsletter_consent"]
        self.pro.engagements = [
            engagement for engagement in self.chosen if engagement not in (EVENTS, OTHER)
        ]
