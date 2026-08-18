from ..base import BaseService
from ..jobirl_api.register_user import RegisterUserOnJobirl


class CreateMentoree(BaseService):
    def perform(self, *, beneficiary):
        result = RegisterUserOnJobirl(user=beneficiary, is_pro=False)
        if result.failure:
            self.fail_with_errors(result)
        beneficiary.jobirl_user_id = result.user_id
        beneficiary.jobirl_user_token = result.token
        beneficiary.save()
