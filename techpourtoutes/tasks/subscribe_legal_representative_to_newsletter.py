from celery import shared_task

from techpourtoutes.services.legal_representative_authorization.subscribe_to_newsletter import (
    SubscribeLegalRepresentativeToNewsletter,
)

from ._retry import RETRY_KWARGS, raise_failure


@shared_task(bind=True, **RETRY_KWARGS)
def subscribe_legal_representative_to_newsletter_task(self, email: str):
    result = SubscribeLegalRepresentativeToNewsletter(email=email)
    if result.failure:
        raise_failure(result)
