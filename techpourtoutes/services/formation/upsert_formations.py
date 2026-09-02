from techpourtoutes.models import Formation
from techpourtoutes.services.base import BaseService
from techpourtoutes.utils.onisep import (
    domains_from_raw,
    duration_in_years,
    level_from_exit_level,
    onisep_id_from_url,
    sub_domains_from_raw,
)
from techpourtoutes.utils.text import capitalize_first, strip_accents

MAPPED_FIELDS = [
    "code_nsf",
    "code_scolarite",
    "type_acronym",
    "type_name",
    "name",
    "name_normalized",
    "acronym",
    "duration_in_years",
    "exit_level",
    "code_rncp",
    "certification_level",
    "certification_level_name",
    "domains",
    "sub_domains",
]


class UpsertFormations(BaseService):
    def perform(self, *, records) -> None:
        formations = self._formations_by_onisep_id(records)
        Formation.objects.bulk_create(
            list(formations.values()),
            update_conflicts=True,
            unique_fields=["onisep_id"],
            update_fields=MAPPED_FIELDS,
            batch_size=1000,
        )

    def _formations_by_onisep_id(self, records):
        formations = {}
        for record in records:
            onisep_id = onisep_id_from_url(record.get("url_et_id_onisep"))
            if not onisep_id or not record.get("libelle_formation_principal"):
                continue
            formations[onisep_id] = self._formation(record, onisep_id)
        return formations

    def _formation(self, record, onisep_id):
        name = capitalize_first(record["libelle_formation_principal"])
        return Formation(
            onisep_id=onisep_id,
            code_nsf=record.get("code_nsf") or "",
            code_scolarite=record.get("code_scolarite") or "",
            type_acronym=record.get("sigle_type_formation") or "",
            type_name=record.get("libelle_type_formation") or "",
            name=name,
            # `bulk_create` bypasses `save()`, so the normalized column is computed here.
            name_normalized=strip_accents(name),
            acronym=record.get("sigle_formation") or "",
            duration_in_years=duration_in_years(record.get("duree")),
            exit_level=level_from_exit_level(record.get("niveau_de_sortie_indicatif")),
            code_rncp=record.get("code_rncp") or "",
            certification_level=record.get("niveau_de_certification") or "",
            certification_level_name=record.get("libelle_niveau_de_certification") or "",
            domains=domains_from_raw(record.get("domainesous-domaine")),
            sub_domains=sub_domains_from_raw(record.get("domainesous-domaine")),
        )
