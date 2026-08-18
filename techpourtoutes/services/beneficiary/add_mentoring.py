from ...utils.dates import compute_age
from ..base import BaseService
from .sign_up_for_mentoring import SignUpForMentoring


class AddMentoring(BaseService):
    def perform(self, *, beneficiary, mentoring_signup_data):
        is_minor = compute_age(beneficiary.birth_date) < 18
        beneficiary.phone = mentoring_signup_data["phone"]
        if is_minor:
            beneficiary.legal_representative_name = mentoring_signup_data[
                "legal_representative_name"
            ]
            beneficiary.legal_representative_email = mentoring_signup_data[
                "legal_representative_email"
            ]
        beneficiary.save()

        result = SignUpForMentoring(
            beneficiary=beneficiary,
            is_minor=is_minor,
            mentoring_signup_data=mentoring_signup_data,
        )
        if result.failure:
            self.fail_with_errors(result)
