from techpourtoutes.services.jobirl_api.base_service import JobirlApiBaseService


class RefreshAccessToken(JobirlApiBaseService):
    def perform(self, *, user) -> None:
        self.request(
            method="post",
            path="user_refresh_access_token",
            data={"iduser": user.jobirl_user_id, "token": user.jobirl_user_token},
        )

        self.token = self.jobirl_response_body["token"]
        user.jobirl_user_token = self.token
        user.save()
