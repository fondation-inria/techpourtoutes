from django.db import transaction

from ...tasks import create_mentoree_task
from ..base import BaseService
from ..legal_representative_authorization.request_authorization import (
    RequestLegalRepresentativeAuthorization,
)
from .create_mentoree import CreateMentoree


class SignUpForMentoring(BaseService):
    def perform(self, *, beneficiary, is_minor, mentoring_signup_data):
        if is_minor:
            RequestLegalRepresentativeAuthorization(
                beneficiary=beneficiary,
                legal_representative_name=mentoring_signup_data["legal_representative_name"],
                legal_representative_email=mentoring_signup_data["legal_representative_email"],
            )
            return
        result = CreateMentoree(beneficiary=beneficiary)
        if result.success:
            return
        if not result.failed_with_transient_error:
            self.fail_with_errors(result)
        self._retry_in_the_background(beneficiary)

    def _retry_in_the_background(self, beneficiary):
        # Only after the commit: the worker must not look for a beneficiary nobody wrote yet.
        transaction.on_commit(
            lambda: create_mentoree_task.delay(beneficiary_pk=str(beneficiary.pk))
        )
