from ..mailers import MentorMailer
from .base import BaseService
from .jobirl_api.register_mentor import RegisterMentorOnJobirl


class CreateMentor(BaseService):
    def perform(self, *, mentor):
        result = RegisterMentorOnJobirl(mentor=mentor)
        if result.failure:
            self.errors.extend(result.errors)
            return
        mentor.jobirl_user_id = result.user_id
        mentor.jobirl_user_token = result.token
        mentor.save()
        MentorMailer.welcome(mentor=mentor)
        self.mentor = mentor
