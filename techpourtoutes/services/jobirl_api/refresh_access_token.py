from techpourtoutes.services.jobirl_api.base_service import JobirlApiBaseService


class RefreshAccessToken(JobirlApiBaseService):
    def perform(self, *, pro) -> None:
        self.request(
            method="post",
            path="user_refresh_access_token",
            data={"iduser": pro.jobirl_user_id, "token": pro.jobirl_user_token},
        )

        self.token = self.jobirl_response_body["token"]
        pro.jobirl_user_token = self.token
        pro.save()
