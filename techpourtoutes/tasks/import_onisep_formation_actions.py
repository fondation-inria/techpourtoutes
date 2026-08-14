from celery import shared_task

from techpourtoutes.services.formation_action.import_formation_actions import (
    ImportFormationActions,
)

from ._retry import RETRY_KWARGS, TransientError


@shared_task(bind=True, **RETRY_KWARGS)
def import_onisep_formation_actions_task(self, scope: str = "all", sample: bool = False):
    result = ImportFormationActions(scope=scope, sample=sample)
    if result.failure:
        message = ", ".join(result.errors)
        if result.failed_with_transient_error():
            raise TransientError(message)
        raise RuntimeError(message)
