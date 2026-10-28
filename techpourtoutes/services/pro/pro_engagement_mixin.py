from django.db import transaction

from ...forms.pro_inscription import OTHER
from ...forms.pro_inscription.workshop_request_form import OTHER_SCHOOL_MISSION
from ...mailers import ConsortiumMailer, ProMailer
from ...models import Pro, WorkshopRequest
from ...tasks import notify_workshop_request_task
from ...utils.missing_record import report_missing_record
from .create_mentor import CreateMentor

# The engagements the team is told about by mail; the others have their own follow-up.
_NOTIFIED_ENGAGEMENTS = (
    Pro.Engagement.INTERNSHIPS,
    Pro.Engagement.WORK_AMBASSADOR,
    Pro.Engagement.SPONSOR,
    Pro.Engagement.MOBILIZE_STRUCTURE,
    OTHER,
)


class ProEngagementMixin:
    """What taking on engagements does to `self.pro`, whether she signs up with them or adds one
    later. Her answers override one another in this order: the additional information, then the
    workshop request, then the training ambassador's. The service names its `origin`."""

    origin = ""

    def _save_pro_with(
        self, training_ambassador_form, workshop_request_form, additional_information
    ):
        """Applies her answers to `self.pro`, then saves her along with what they call for. The
        forms are kept for `_notify_about_engagements`."""
        self.training_ambassador_form = training_ambassador_form
        self.workshop_request_form = workshop_request_form
        if training_ambassador_form:
            self.pro.structure_type = Pro.StructureType.HIGHER_ED
            self.pro.structure_name = training_ambassador_form.school.name
            if training_ambassador_form.cleaned_data["phone"]:
                self.pro.phone = training_ambassador_form.cleaned_data["phone"]
        if workshop_request_form:
            self._apply_workshop_request(workshop_request_form)
        if additional_information:
            self._apply_additional_information(additional_information)

        with transaction.atomic():
            self._save_pro()
            if training_ambassador_form:
                self.training_experience = training_ambassador_form.save(self.pro)
            if workshop_request_form:
                for workshop in workshop_request_form.cleaned_data["ateliers"]:
                    WorkshopRequest.objects.create(
                        pro=self.pro,
                        type=workshop,
                        remark=workshop_request_form.cleaned_data["remark"],
                    )

    # Only once everything is saved: the team and Latitudes must find what they are told about.
    def _notify_about_engagements(self, engagements, messages=None):
        """`messages` holds what she wrote the team, by engagement."""
        for engagement in _NOTIFIED_ENGAGEMENTS:
            if engagement in engagements:
                ConsortiumMailer.pro_signed_up(
                    pro=self.pro,
                    engagement=engagement,
                    message=(messages or {}).get(engagement, ""),
                )
        if self.training_ambassador_form:
            ConsortiumMailer.training_ambassador_signed_up(
                pro=self.pro, training_experience=self.training_experience
            )
            report_missing_record(self.training_ambassador_form, self.pro, self.origin)
            ProMailer.welcome_training_ambassador(pro=self.pro)
        if self.workshop_request_form:
            answers = self.workshop_request_form.cleaned_data
            notify_workshop_request_task.delay(
                pro_pk=str(self.pro.pk),
                ateliers=answers["ateliers"],
                remark=answers["remark"],
                structure_uai=answers["structure_uai"],
            )
            report_missing_record(self.workshop_request_form, self.pro, self.origin)

    # The school she asks a workshop for is her structure only when she works there, and the job
    # she gave hers only when the list named it.
    def _apply_workshop_request(self, form):
        if form.works_at_school:
            self.pro.structure_type = Pro.StructureType.SCHOOL
            self.pro.structure_name = form.cleaned_data["school_label"]
            if form.cleaned_data["job_title"] != OTHER_SCHOOL_MISSION:
                self.pro.job_title = form.cleaned_data["job_title"]

    def _apply_additional_information(self, answers):
        for field in ("structure_type", "structure_name", "job_title", "phone", "postal_code"):
            setattr(self.pro, field, answers[field])

    def _save_pro(self):
        if Pro.Engagement.MENTOR not in self.pro.engagements:
            self.pro.save()
            return
        result = CreateMentor(pro=self.pro)
        if result.failure:
            self.fail_with_errors(result)
