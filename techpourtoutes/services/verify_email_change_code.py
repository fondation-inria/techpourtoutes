from django.urls import reverse

from techpourtoutes.mailers import AuthMailer
from techpourtoutes.models.user import EMAIL_CHANGE_MAX_ATTEMPTS

from .base import BaseService


class VerifyEmailChangeCode(BaseService):
    def perform(self, *, user, payload, code):
        if not user.verify_email_change_code(code):
            if user.email_change_attempts >= EMAIL_CHANGE_MAX_ATTEMPTS:
                user.clear_email_change()
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
