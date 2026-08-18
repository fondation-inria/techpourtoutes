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


class CreateBeneficiary(BaseService):
    def perform(
        self,
        *,
        email,
        first_name,
        last_name,
        birth_date,
        newsletter_consent,
        training_experience_form,
        wants_mentor,
        mentoring_signup_data=None,
    ):
        is_minor = compute_age(birth_date) < 18
        with transaction.atomic():
            self.beneficiary = self._create_beneficiary(
                email=email,
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                newsletter_consent=newsletter_consent,
                wants_mentor=wants_mentor,
                is_minor=is_minor,
                mentoring_signup_data=mentoring_signup_data,
            )
            self._create_training_experience(training_experience_form)
            if wants_mentor:
                self._sign_up_for_mentoring(is_minor, mentoring_signup_data)
        self._trigger_onboarding(training_experience_form)

    def _create_beneficiary(
        self,
        *,
        email,
        first_name,
        last_name,
        birth_date,
        newsletter_consent,
        wants_mentor,
        is_minor,
        mentoring_signup_data,
    ):
        beneficiary = Beneficiary(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            brevo_sync_enabled=newsletter_consent,
            phone=mentoring_signup_data["phone"] if wants_mentor else "",
            legal_representative_name=(
                mentoring_signup_data["legal_representative_name"]
                if wants_mentor and is_minor
                else ""
            ),
            legal_representative_email=(
                mentoring_signup_data["legal_representative_email"]
                if wants_mentor and is_minor
                else ""
            ),
        )
        beneficiary.save()
        return beneficiary

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

    def _trigger_onboarding(self, training_experience_form):
        AuthMailer.login_code(user=self.beneficiary, code=self.beneficiary.issue_login_code())
        report_missing_record(training_experience_form, self.beneficiary, "Funnel d'inscription")
        send_beneficiary_welcome_email_task.apply_async(
            kwargs={"beneficiary_pk": str(self.beneficiary.pk)},
            countdown=_WELCOME_EMAIL_DELAY_SECONDS,
        )
