from celery import shared_task

from techpourtoutes.mailers.beneficiary_mailer import BeneficiaryMailer
from techpourtoutes.models import Beneficiary, Event


@shared_task
def send_event_updated_email_task(event_pk: str, beneficiary_pk: str):
    BeneficiaryMailer.event_updated(
        event=Event.objects.get(pk=event_pk),
        beneficiary=Beneficiary.objects.get(pk=beneficiary_pk),
    )
