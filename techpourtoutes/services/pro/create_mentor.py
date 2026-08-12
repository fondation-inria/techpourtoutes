from ...mailers import ProMailer
from ..base import BaseService
from ..jobirl_api.register_user import RegisterUserOnJobirl


class CreateMentor(BaseService):
    def perform(self, *, pro):
        result = RegisterUserOnJobirl(user=pro)
        if result.failure:
            self.errors.extend(result.errors)
            return
        pro.engagements = [*pro.engagements, "mentor"]
        pro.jobirl_user_id = result.user_id
        pro.jobirl_user_token = result.token
        already_exists = pro.pk is not None
        pro.save()
        if already_exists:
            ProMailer.new_engagement(pro=pro)
        else:
            ProMailer.welcome(pro=pro, token=pro.issue_login_token())
