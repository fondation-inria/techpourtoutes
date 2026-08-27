from techpourtoutes.models import FormationAction
from techpourtoutes.services.base import BaseService


class PruneFormationActions(BaseService):
    """Drop the links the Onisep feed no longer carries, sparing those a parcours relies on.

    A spared link keeps joining its formation to its établissement, and only loses the
    identifier that ties it to a feed which does not describe it anymore.
    """

    def perform(self, *, active_onisep_ids: set[str]) -> None:
        obsolete = FormationAction.objects.exclude(onisep_id__in=active_onisep_ids)
        spared = list(obsolete.backing_a_parcours().values_list("pk", flat=True))
        obsolete.exclude(pk__in=spared).delete()
        FormationAction.objects.filter(pk__in=spared).update(onisep_id=None)
