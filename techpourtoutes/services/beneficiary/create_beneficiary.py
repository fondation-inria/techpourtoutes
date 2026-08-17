from ...mailers import AuthMailer, ConsortiumMailer
from ...models import Beneficiary
from ...tasks import send_beneficiary_welcome_email_task
from ...utils.dates import compute_age
from ...utils.missing_record import report_missing_record
from ..base import BaseService
from .create_mentoree import CreateMentoree

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
        self.mentoring_errors = []
        is_minor = compute_age(birth_date) < 18
        self.beneficiary = self._create_beneficiary(
            email=email,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            newsletter_consent=newsletter_consent,
            training_experience_form=training_experience_form,
            wants_mentor=wants_mentor,
            is_minor=is_minor,
            mentoring_signup_data=mentoring_signup_data,
        )
        if wants_mentor:
            self._signup_for_mentoring(is_minor, mentoring_signup_data)

    def _create_beneficiary(
        self,
        *,
        email,
        first_name,
        last_name,
        birth_date,
        newsletter_consent,
        training_experience_form,
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
        training_experience_form.save(beneficiary)
        report_missing_record(training_experience_form, beneficiary, "Funnel d'inscription")
        AuthMailer.login_code(user=beneficiary, code=beneficiary.issue_login_code())
        send_beneficiary_welcome_email_task.apply_async(
            kwargs={"beneficiary_pk": str(beneficiary.pk)},
            countdown=_WELCOME_EMAIL_DELAY_SECONDS,
        )
        return beneficiary

    def _signup_for_mentoring(self, is_minor, mentoring_signup_data):
        if is_minor:
            ConsortiumMailer.new_mentoring_signup(
                beneficiary=self.beneficiary, mentoring_signup_data=mentoring_signup_data
            )
            return
        result = CreateMentoree(beneficiary=self.beneficiary)
        if result.failure:
            self.mentoring_errors.extend(result.errors)
