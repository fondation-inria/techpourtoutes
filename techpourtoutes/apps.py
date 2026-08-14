from django.apps import AppConfig


class TechpourtoutesConfig(AppConfig):
    name = "techpourtoutes"

    def ready(self):
        from .models import Beneficiary, Pro
        from .signals import connect_brevo_sync

        connect_brevo_sync(Beneficiary)
        connect_brevo_sync(Pro)
