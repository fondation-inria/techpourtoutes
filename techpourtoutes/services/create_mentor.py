from ..mailers import MentorMailer
from .base import BaseService
from .jobirl_api.register_mentor import RegisterMentorOnJobirl


class CreateMentor(BaseService):
    def perform(self, *, pro):
        result = RegisterMentorOnJobirl(pro=pro)
        if result.failure:
            self.errors.extend(result.errors)
            return
        pro.jobirl_user_id = result.user_id
        pro.jobirl_user_token = result.token
        pro.save()
        MentorMailer.welcome(mentor=pro)
