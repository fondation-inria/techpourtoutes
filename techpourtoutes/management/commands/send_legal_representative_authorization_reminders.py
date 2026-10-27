from django.core.management.base import BaseCommand

from techpourtoutes.services.legal_representative_authorization.send_reminders import (
    SendLegalRepresentativeAuthorizationReminders,
)


class Command(BaseCommand):
    help = (
        "Remind the legal representatives who have not signed the authorization yet, and the "
        "beneficiaries who have been waiting for it for two weeks. Run once a day."
    )

    def handle(self, *args, **options):
        result = SendLegalRepresentativeAuthorizationReminders()
        self.stdout.write(
            self.style.SUCCESS(
                f"  {result.legal_representatives_reminded} relance(s) envoyée(s) aux personnes "
                "responsables légales."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"  {result.beneficiaries_reminded} relance(s) envoyée(s) aux bénéficiaires."
            )
        )
