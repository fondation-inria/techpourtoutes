from techpourtoutes.services.jobirl_api.base_service import JobirlApiBaseService


class RefreshAccessToken(JobirlApiBaseService):
    def perform(self, *, mentor) -> None:
        self.request(
            method="post",
            path="user_refresh_access_token",
            payload={"iduser": mentor.jobirl_user_id, "token": mentor.jobirl_user_token},
        )

        self.token = self.jobirl_response_body["token"]
        mentor.jobirl_user_token = self.token
        mentor.save()
