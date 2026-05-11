from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


class MentorMailer:
    @classmethod
    def welcome(cls, *, mentor):
        context = {"mentor": mentor}
        send_mail(
            subject="Bienvenue dans la Coallition !",
            message=render_to_string("emails/mentor_welcome.txt", context),
            html_message=render_to_string("emails/mentor_welcome.html", context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[mentor.email],
        )
