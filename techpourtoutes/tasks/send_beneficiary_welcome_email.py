from celery import shared_task

from techpourtoutes.mailers.beneficiary_mailer import BeneficiaryMailer
from techpourtoutes.models import Beneficiary


@shared_task
def send_beneficiary_welcome_email_task(beneficiary_pk: str):
    beneficiary = Beneficiary.objects.get(pk=beneficiary_pk)
    BeneficiaryMailer.welcome(beneficiary=beneficiary)
