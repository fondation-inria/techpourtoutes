from django.urls import reverse

from techpourtoutes.mailers import AuthMailer

from .base import BaseService


class VerifyEmailChangeCode(BaseService):
    def perform(self, *, user, payload, code):
        if not user.consume_email_change_code(code):
            self.fail("Code invalide ou expiré.")

        stage, new_email = payload["stage"], payload["new_email"]
        if stage == "current":
            new_code = user.set_email_change_code()
            AuthMailer.change_email(user=user, code=new_code, new_email=new_email)
            self.redirect_url = user.email_change_verify_url(
                user.issue_email_change_token(new_email, "new")
            )
        else:
            user.apply_email_change(new_email)
            self.redirect_url = reverse("account")
