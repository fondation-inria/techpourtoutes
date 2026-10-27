from django.db import transaction

from ...mailers import AuthMailer, ConsortiumMailer
from ...models import Beneficiary
from ...tasks import send_beneficiary_welcome_email_task
from ...utils.dates import compute_age
from ...utils.missing_record import report_missing_record
from ..base import BaseService
from .notify_makeuse_project_submission import NotifyMakeuseProjectSubmission
from .sign_up_for_mentoring import SignUpForMentoring

# Delay before the welcome email is sent, so it doesn't land before the login code.
_WELCOME_EMAIL_DELAY_SECONDS = 5 * 60


class UpsertBeneficiary(BaseService):
    def perform(
        self,
        *,
        beneficiary=None,
        beneficiary_data=None,
        training_experience_form=None,
        mentoring_signup_data=None,
        training_ambassador_request_data=None,
        makeuse_project_submission_data=None,
    ):
        is_new = beneficiary is None
        self.beneficiary = beneficiary or Beneficiary(
            username=beneficiary_data["email"], email=beneficiary_data["email"]
        )
        if beneficiary_data:
            self.beneficiary.birth_date = beneficiary_data["birth_date"]
        is_minor = compute_age(self.beneficiary.birth_date) < 18
        with transaction.atomic():
            self._save_beneficiary(
                beneficiary_data=beneficiary_data,
                training_experience_form=training_experience_form,
                mentoring_signup_data=mentoring_signup_data,
                training_ambassador_request_data=training_ambassador_request_data,
            )
            if training_experience_form:
                self._create_training_experience(training_experience_form)
            if mentoring_signup_data:
                self._sign_up_for_mentoring(is_minor, mentoring_signup_data)
        if training_ambassador_request_data:
            ConsortiumMailer.training_ambassador_requested(
                beneficiary=self.beneficiary, topic=training_ambassador_request_data["topic"]
            )
        if makeuse_project_submission_data:
            NotifyMakeuseProjectSubmission(
                beneficiary=self.beneficiary, **makeuse_project_submission_data
            )
        if training_experience_form:
            report_missing_record(training_experience_form, self.beneficiary)
        if is_new:
            self._trigger_onboarding()

    def _save_beneficiary(
        self,
        *,
        beneficiary_data,
        training_experience_form,
        mentoring_signup_data,
        training_ambassador_request_data,
    ):
        if beneficiary_data:
            self._apply_identity(beneficiary_data)
        if training_experience_form and not self.beneficiary.postal_code:
            self.beneficiary.postal_code = training_experience_form.out_of_scope_postal_code
        if mentoring_signup_data:
            self.beneficiary.phone = mentoring_signup_data["phone"]
            if mentoring_signup_data["postal_code"]:
                self.beneficiary.postal_code = mentoring_signup_data["postal_code"]
        if training_ambassador_request_data:
            self.beneficiary.has_requested_training_ambassador = True
        self.beneficiary.save()

    def _apply_identity(self, beneficiary_data):
        self.beneficiary.first_name = beneficiary_data["first_name"]
        self.beneficiary.last_name = beneficiary_data["last_name"]
        self.beneficiary.brevo_sync_enabled = beneficiary_data["newsletter_consent"]

    def _create_training_experience(self, training_experience_form):
        training_experience_form.save(self.beneficiary)

    def _sign_up_for_mentoring(self, is_minor, mentoring_signup_data):
        result = SignUpForMentoring(
            beneficiary=self.beneficiary,
            is_minor=is_minor,
            mentoring_signup_data=mentoring_signup_data,
        )
        if result.failure:
            self.fail_with_errors(result)

    def _trigger_onboarding(self):
        AuthMailer.login_code(user=self.beneficiary, code=self.beneficiary.issue_login_code())
        send_beneficiary_welcome_email_task.apply_async(
            kwargs={"beneficiary_pk": str(self.beneficiary.pk)},
            countdown=_WELCOME_EMAIL_DELAY_SECONDS,
        )
