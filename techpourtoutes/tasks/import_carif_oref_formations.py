from celery import shared_task

from techpourtoutes.services.formation.import_carif_oref_formations import (
    ImportCarifOrefFormations,
)

from ._retry import RETRY_KWARGS, raise_failure


@shared_task(bind=True, **RETRY_KWARGS)
def import_carif_oref_formations_task(self):
    result = ImportCarifOrefFormations()
    if result.failure:
        raise_failure(result)
