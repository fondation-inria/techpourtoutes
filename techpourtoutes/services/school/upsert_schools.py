from techpourtoutes.models import School
from techpourtoutes.services.base import BaseService
from techpourtoutes.utils.onisep import onisep_id_from_url, split_parent_label
from techpourtoutes.utils.phone import parse_school_phone
from techpourtoutes.utils.text import strip_accents

UNKNOWN_SCOPE_MESSAGE = "Périmètre d'import inconnu : {scope}."

SCOPE_FLAGS = {"secondary": "secondary", "higher_ed": "higher_ed"}

MAPPED_FIELDS = [
    "uai",
    "siret",
    "type",
    "name",
    "name_normalized",
    "acronym",
    "acronym_normalized",
    "status",
    "parent_uai",
    "parent_onisep_id",
    "mailbox",
    "address",
    "postal_code",
    "city",
    "cog_code",
    "cedex",
    "phone",
    "borough",
    "department",
    "academy",
    "region",
    "region_code",
    "longitude",
    "latitude",
]


class UpsertSchools(BaseService):
    def perform(self, *, records, scope: str) -> None:
        flag = SCOPE_FLAGS.get(scope)
        if flag is None:
            self.fail(UNKNOWN_SCOPE_MESSAGE.format(scope=scope))
            return

        schools = self._schools_by_onisep_id(records, flag)
        School.objects.bulk_create(
            list(schools.values()),
            update_conflicts=True,
            unique_fields=["onisep_id"],
            update_fields=[*MAPPED_FIELDS, flag],
            batch_size=1000,
        )

    def _schools_by_onisep_id(self, records, flag):
        schools = {}
        for record in records:
            onisep_id = onisep_id_from_url(record.get("url_et_id_onisep"))
            if not onisep_id or not record.get("nom"):
                continue
            schools[onisep_id] = self._school(record, onisep_id, flag)
        return schools

    def _school(self, record, onisep_id, flag):
        parent_name, parent_uai = split_parent_label(
            record.get("universite_de_rattachement_libelle_et_uai")
        )
        name = f"{parent_name} - {record['nom']}" if parent_name else record["nom"]
        acronym = record.get("sigle") or ""
        return School(
            onisep_id=onisep_id,
            uai=record.get("code_uai") or "",
            siret=record.get("n_siret") or "",
            type=record.get("type_detablissement") or "",
            name=name,
            # `bulk_create` bypasses `save()`, so the normalized columns are computed here.
            name_normalized=strip_accents(name),
            acronym=acronym,
            acronym_normalized=strip_accents(acronym),
            status=record.get("statut") or "",
            parent_uai=parent_uai,
            parent_onisep_id=(
                onisep_id_from_url(record.get("universite_de_rattachement_id_et_url_onisep"))
                if parent_name
                else ""
            ),
            mailbox=record.get("boite_postale") or "",
            address=record.get("adresse") or "",
            postal_code=record.get("cp") or "",
            city=record.get("commune") or "",
            cog_code=record.get("commune_cog") or "",
            cedex=record.get("cedex") or "",
            phone=parse_school_phone(record.get("telephone")),
            borough=record.get("arrondissement") or "",
            department=record.get("departement") or "",
            academy=record.get("academie") or "",
            region=record.get("region") or "",
            region_code=record.get("region_cog") or "",
            longitude=_coordinate(record.get("longitude_x")),
            latitude=_coordinate(record.get("latitude_y")),
            **{flag: True},
        )


def _coordinate(value):
    """Native floats from the API, strings from the seed CSV, blanks from either."""
    try:
        return float(value)
    except TypeError, ValueError:
        return None
