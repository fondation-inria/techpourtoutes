from techpourtoutes.models import Formation, FormationAction, School
from techpourtoutes.services.base import BaseService
from techpourtoutes.utils.onisep import onisep_id_from_url


class UpsertFormationActions(BaseService):
    """Upsert the links between a formation and the schools that delivers it.

    Both ends are resolved against dicts loaded up front — 70 000 rows would otherwise mean as
    many queries — and a row pointing at an unknown end is skipped rather than left to blow up
    on the foreign key.
    """

    def perform(self, *, records) -> None:
        formation_pks = dict(Formation.objects.values_list("onisep_id", "pk"))
        school_pks = dict(School.objects.values_list("onisep_id", "pk"))

        actions = {}
        for record in records:
            action = self._action(record, formation_pks, school_pks)
            if action is not None:
                actions[action.onisep_id] = action

        FormationAction.objects.bulk_create(
            list(actions.values()),
            update_conflicts=True,
            unique_fields=["onisep_id"],
            update_fields=["formation_id", "school_id"],
            batch_size=1000,
        )

    def _action(self, record, formation_pks, school_pks):
        onisep_id = onisep_id_from_url(record.get("action_de_formation_af_identifiant_onisep"))
        formation_pk = formation_pks.get(onisep_id_from_url(record.get("for_url_et_id_onisep")))
        school_pk = school_pks.get(onisep_id_from_url(record.get("ens_url_et_id_onisep")))
        if not onisep_id or formation_pk is None or school_pk is None:
            return None
        return FormationAction(onisep_id=onisep_id, formation_id=formation_pk, school_id=school_pk)
