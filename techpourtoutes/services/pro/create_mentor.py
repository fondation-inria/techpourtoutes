from django.db import transaction

from ...mailers import ProMailer
from ...models import Pro
from ...tasks import create_mentor_task
from ..base import BaseService
from ..jobirl_api.register_user import RegisterUserOnJobirl


class CreateMentor(BaseService):
    def perform(self, *, pro):
        self.pro = pro
        already_registered = pro.pk is not None
        with transaction.atomic():
            # Jobirl first: a refusal must leave the pro exactly as the view handed her over,
            # since that same instance is what gets re-rendered with the error.
            self._register_on_jobirl()
            pro.add_engagement(Pro.Engagement.MENTOR)
            pro.save()
        self._trigger_onboarding(already_registered)

    def _register_on_jobirl(self):
        result = RegisterUserOnJobirl(user=self.pro, is_pro=True)
        if result.failure:
            self._handle_registration_failure(result)
            return
        self.pro.jobirl_user_id = result.user_id
        self.pro.jobirl_user_token = result.token

    def _handle_registration_failure(self, result):
        if not result.failed_with_transient_error:
            self.fail_with_errors(result)
        # Only after the commit: the worker must not look for a pro nobody wrote yet.
        transaction.on_commit(lambda: create_mentor_task.delay(pro_pk=str(self.pro.pk)))

    def _trigger_onboarding(self, already_registered):
        if already_registered:
            ProMailer.new_engagement(pro=self.pro)
        else:
            ProMailer.welcome(pro=self.pro, token=self.pro.issue_login_token())
