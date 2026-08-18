from django.db import transaction

from ...mailers import ConsortiumMailer
from ...tasks import create_mentoree_task
from ..base import BaseService
from .create_mentoree import CreateMentoree


class SignUpForMentoring(BaseService):
    def perform(self, *, beneficiary, is_minor, mentoring_signup_data):
        if is_minor:
            ConsortiumMailer.new_mentoring_signup(
                beneficiary=beneficiary, mentoring_signup_data=mentoring_signup_data
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
