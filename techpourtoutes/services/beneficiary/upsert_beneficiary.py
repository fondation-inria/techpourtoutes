from django.db import transaction

from ...mailers import AuthMailer
from ...models import Beneficiary
from ...tasks import send_beneficiary_welcome_email_task
from ...utils.dates import compute_age
from ...utils.missing_record import report_missing_record
from ..base import BaseService
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
    ):
        is_new = beneficiary is None
        self.beneficiary = beneficiary or Beneficiary(
            username=beneficiary_data["email"], email=beneficiary_data["email"]
        )
        birth_date = (
            beneficiary_data["birth_date"] if beneficiary_data else self.beneficiary.birth_date
        )
        is_minor = compute_age(birth_date) < 18
        with transaction.atomic():
            self._save_beneficiary(
                beneficiary_data=beneficiary_data,
                is_minor=is_minor,
                mentoring_signup_data=mentoring_signup_data,
            )
            if training_experience_form:
                self._create_training_experience(training_experience_form)
            if mentoring_signup_data:
                self._sign_up_for_mentoring(is_minor, mentoring_signup_data)
        if training_experience_form:
            report_missing_record(
                training_experience_form, self.beneficiary, "Funnel d'inscription"
            )
        if is_new:
            self._trigger_onboarding()

    def _save_beneficiary(self, *, beneficiary_data, is_minor, mentoring_signup_data):
        if beneficiary_data:
            self._apply_identity(beneficiary_data)
        if mentoring_signup_data:
            self._apply_mentoring_contact(mentoring_signup_data, is_minor)
        self.beneficiary.save()

    def _apply_identity(self, beneficiary_data):
        self.beneficiary.first_name = beneficiary_data["first_name"]
        self.beneficiary.last_name = beneficiary_data["last_name"]
        self.beneficiary.birth_date = beneficiary_data["birth_date"]
        self.beneficiary.brevo_sync_enabled = beneficiary_data["newsletter_consent"]

    def _apply_mentoring_contact(self, mentoring_signup_data, is_minor):
        self.beneficiary.phone = mentoring_signup_data["phone"]
        # An adult never has a legal representative, even if the form data carried one.
        self.beneficiary.legal_representative_name = (
            mentoring_signup_data["legal_representative_name"] if is_minor else ""
        )
        self.beneficiary.legal_representative_email = (
            mentoring_signup_data["legal_representative_email"] if is_minor else ""
        )

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
