from base64 import b32encode

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_totp.models import TOTPDevice


class Command(BaseCommand):
    help = "Create a confirmed TOTP (2FA) device for a user and print its secret key."

    def add_arguments(self, parser):
        parser.add_argument("email")

    def handle(self, *args, **options):
        email = options["email"]
        user = get_user_model().objects.filter(email=email).first()
        if user is None:
            raise CommandError(f"No user found with email {email!r}.")
        device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        self.stdout.write(b32encode(device.bin_key).decode())
