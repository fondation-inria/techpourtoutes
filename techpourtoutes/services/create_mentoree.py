from .base import BaseService
from .jobirl_api.register_mentor import RegisterMentorOnJobirl


class CreateMentoree(BaseService):
    def perform(self, *, beneficiary):
        result = RegisterMentorOnJobirl(user=beneficiary)
        if result.failure:
            self.errors.extend(result.errors)
            return
        beneficiary.jobirl_user_id = result.user_id
        beneficiary.jobirl_user_token = result.token
        beneficiary.save()
