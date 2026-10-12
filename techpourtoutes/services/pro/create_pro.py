from django.db import transaction

from ...forms.pro_inscription import EVENTS, OTHER
from ...mailers import ConsortiumMailer, ProMailer
from ...models import Pro, WorkshopRequest
from ...tasks import notify_workshop_request_task
from ...utils.missing_record import report_missing_record
from ..base import BaseService
from .create_mentor import CreateMentor

_ORIGIN = "Funnel d'inscription pro"

# The engagements the team is told about by mail; the others have their own follow-up.
_NOTIFIED_ENGAGEMENTS = (
    Pro.Engagement.INTERNSHIPS,
    Pro.Engagement.WORK_AMBASSADOR,
    Pro.Engagement.SPONSOR,
    Pro.Engagement.MOBILIZE_STRUCTURE,
)

_SITUATIONS = {
    Pro.StructureType.RETIRED: Pro.ProfessionalSituation.RETIRED,
    Pro.StructureType.JOBLESS: Pro.ProfessionalSituation.JOBLESS,
}


class CreatePro(BaseService):
    """Creates the pro who went through the inscription funnel, along with what each of her
    engagements calls for. Every screen she answered overrides the ones before it: the last
    information, then the workshop request, then the training ambassador screen."""

    def perform(
        self,
        *,
        identity,
        engagements,
        training_ambassador_form=None,
        workshop_request_form=None,
        last_information=None,
    ):
        self.chosen = engagements["engagements"]
        self.pro = Pro(username=identity["email"], email=identity["email"])
        self._apply_identity(identity)
        if training_ambassador_form:
            self._apply_training_ambassador(training_ambassador_form.cleaned_data)
        if workshop_request_form:
            self._apply_workshop_request(workshop_request_form.cleaned_data)
        if last_information:
            self._apply_last_information(last_information)

        with transaction.atomic():
            self._save_pro()
            if training_ambassador_form:
                self.training_experience = training_ambassador_form.save(self.pro)
            if workshop_request_form:
                self._create_workshop_requests(workshop_request_form.cleaned_data)

        ProMailer.welcome(pro=self.pro, code=self.pro.issue_login_code())
        self._notify_team(engagements["message"])
        if training_ambassador_form:
            self._onboard_training_ambassador(training_ambassador_form)
        if workshop_request_form:
            self._forward_workshop_request(workshop_request_form)

    def _apply_identity(self, identity):
        self.pro.civility = identity["civility"]
        self.pro.first_name = identity["first_name"]
        self.pro.last_name = identity["last_name"]
        self.pro.brevo_sync_enabled = identity["newsletter_consent"]
        self.pro.engagements = [
            engagement for engagement in self.chosen if engagement not in (EVENTS, OTHER)
        ]

    def _apply_training_ambassador(self, answers):
        self.pro.professional_situation = Pro.ProfessionalSituation.STUDENT
        if answers["phone"]:
            self.pro.phone = answers["phone"]

    def _apply_workshop_request(self, answers):
        self.pro.professional_situation = Pro.ProfessionalSituation.WORKING
        self.pro.structure_name = answers["school_label"]
        self.pro.job_title = answers["job_title"]
        self.pro.postal_code = answers["postal_code"]

    def _apply_last_information(self, answers):
        self.pro.professional_situation = _SITUATIONS.get(
            answers["structure_type"], Pro.ProfessionalSituation.WORKING
        )
        for field in ("structure_type", "structure_name", "job_title", "phone", "postal_code"):
            setattr(self.pro, field, answers[field])

    def _save_pro(self):
        if Pro.Engagement.MENTOR not in self.pro.engagements:
            self.pro.save()
            return
        result = CreateMentor(pro=self.pro)
        if result.failure:
            self.fail_with_errors(result)

    def _create_workshop_requests(self, answers):
        for workshop in answers["ateliers"]:
            WorkshopRequest.objects.create(pro=self.pro, type=workshop, remark=answers["remark"])

    def _notify_team(self, message):
        for engagement in _NOTIFIED_ENGAGEMENTS:
            if engagement in self.pro.engagements:
                ConsortiumMailer.pro_signed_up(pro=self.pro, engagement=engagement)
        if OTHER in self.chosen:
            ConsortiumMailer.other_engagement_requested(pro=self.pro, message=message)

    def _onboard_training_ambassador(self, form):
        ConsortiumMailer.training_ambassador_signed_up(
            pro=self.pro, training_experience=self.training_experience
        )
        report_missing_record(form, self.pro, _ORIGIN)
        ProMailer.welcome_training_ambassador(pro=self.pro)

    def _forward_workshop_request(self, form):
        notify_workshop_request_task.delay(
            pro_pk=str(self.pro.pk),
            ateliers=form.cleaned_data["ateliers"],
            remark=form.cleaned_data["remark"],
            structure_uai=form.cleaned_data["structure_uai"],
        )
        report_missing_record(form, self.pro, _ORIGIN)
