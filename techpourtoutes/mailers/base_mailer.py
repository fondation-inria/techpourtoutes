import re
import sys

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


class BaseMailer:
    """Base for mailers: one method maps to one `.txt` + `.html` template pair.

    A subclass exposes `@classmethod`s that call
    `cls.send_mail(subject=..., recipient_list=..., context=..., tags=...)`. It may set
    `from_email` (otherwise Django falls back to `DEFAULT_FROM_EMAIL`). No other attribute is
    required:
    - the template name is the calling method's name;
    - the folder is derived from the class name (`Mailer` suffix dropped, CamelCase split).

    `tags` are attached to the message and consumed by Anymail's Brevo backend in production;
    other backends ignore them.

    Example: `CoalitionUserMailer.welcome` renders `emails/coalition/user/welcome.{txt,html}`.
    """

    from_email = None

    @classmethod
    def send_mail(cls, *, subject, recipient_list, context=None, tags=None):
        template = sys._getframe(1).f_code.co_name  # retrieves the calling method name
        full_context = cls._base_context() | (context or {})
        message = EmailMultiAlternatives(
            subject=subject,
            body=render_to_string(cls._template_path(template, "txt"), full_context),
            from_email=cls.from_email,
            to=recipient_list,
        )
        message.attach_alternative(
            render_to_string(cls._template_path(template, "html"), full_context), "text/html"
        )
        message.tags = tags or []
        message.send()

    @classmethod
    def _template_path(cls, template, extension):
        segments = re.findall(r"[A-Z][a-z]+", cls.__name__.removesuffix("Mailer"))
        return f"emails/{'/'.join(segments).lower()}/{template}.{extension}"

    @staticmethod
    def _base_context():
        return {
            "logo_url": settings.SITE_URL
            + staticfiles_storage.url("images/techpourtoutes-logo.png"),
            "base_url": settings.SITE_URL,
        }
