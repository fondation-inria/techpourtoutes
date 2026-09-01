from collections import defaultdict

from techpourtoutes.models import Formation, FormationAction, School
from techpourtoutes.services.base import BaseService
from techpourtoutes.utils.carif_oref import (
    certification_level_number,
    is_secondary,
    level_from_certification,
)
from techpourtoutes.utils.onisep import onisep_id_from_url
from techpourtoutes.utils.text import capitalize_first, strip_accents

ROLES = ("formateur", "gestionnaire")


class UpsertCarifOrefFormations(BaseService):
    """Hang the apprenticeship catalogue onto the schools Onisep already gave us.

    This import never creates a school: a record whose own cannot be found is dropped.
    Onisep stays the reference for everything it describes, so a formation it already carries
    is left exactly as it is and only gains a link.
    """

    def perform(self, *, records) -> None:
        self._by_pair, self._by_uai, self._by_siret = self._school_index()
        self._known_formations = dict(Formation.objects.values_list("onisep_id", "pk"))
        self._new_formations = {}
        self._schools_to_flag = defaultdict(set)
        self._links = set()

        for record in records:
            self._read(record)

        self._create_formations()
        self._flag_schools()
        self._create_links()

    def _read(self, record) -> None:
        onisep_id = onisep_id_from_url(record.get("onisep_url"))
        level = certification_level_number(record.get("niveau"))
        schools = self._schools_for(record)
        if not onisep_id or not level_from_certification(level) or not schools:
            return

        formation_pk = self._formation_pk(record, onisep_id, level)
        self._schools_to_flag[_flag(level)] |= set(schools)
        self._links |= {(formation_pk, school_pk) for school_pk in schools}

    def _formation_pk(self, record, onisep_id, level):
        if onisep_id in self._known_formations:
            return self._known_formations[onisep_id]
        if onisep_id not in self._new_formations:
            self._new_formations[onisep_id] = self._formation(record, onisep_id, level)
        return self._new_formations[onisep_id].pk

    def _formation(self, record, onisep_id, level):
        details = record.get("rncp_details") or {}
        name = capitalize_first(record["intitule_rco"])
        return Formation(
            onisep_id=onisep_id,
            code_nsf=details.get("nsf_code") or "",
            type_name=details.get("type_certif") or "",
            type_acronym=details.get("code_type_certif") or "",
            name=name,
            # `bulk_create` bypasses `save()`, so the normalized column is computed here.
            name_normalized=strip_accents(name),
            duration_in_years=int(record["duree"]),
            exit_level=level_from_certification(level),
            certification_level_name=f"niveau {level}",
            **{_flag(level): True},
        )

    def _school_index(self):
        """Three ways into the same table, because the catalogue's SIRET and its UAI each miss
        some rows. Empty identifiers are left out: they would match thousands of them.
        """
        by_pair, by_uai, by_siret = defaultdict(list), defaultdict(list), defaultdict(list)
        for pk, siret, uai in School.objects.values_list("pk", "siret", "uai"):
            if siret and uai:
                by_pair[(siret, uai)].append(pk)
            if uai:
                by_uai[uai].append(pk)
            if siret:
                by_siret[siret].append(pk)
        return by_pair, by_uai, by_siret

    def _schools_for(self, record):
        """The formateur first, then the gestionnaire; for each, both identifiers, then the UAI
        alone, then the SIRET alone. The first key that matches wins, with every row it holds —
        one catalogue entry can legitimately describe several sites.
        """
        for role in ROLES:
            siret = record.get(f"etablissement_{role}_siret") or ""
            uai = record.get(f"etablissement_{role}_uai") or ""
            for schools in (
                self._by_pair.get((siret, uai)),
                self._by_uai.get(uai),
                self._by_siret.get(siret),
            ):
                if schools:
                    return schools
        return []

    def _create_formations(self):
        Formation.objects.bulk_create(
            list(self._new_formations.values()), ignore_conflicts=True, batch_size=1000
        )

    def _flag_schools(self):
        for flag, school_pks in self._schools_to_flag.items():
            School.objects.filter(pk__in=school_pks).update(**{flag: True})

    def _create_links(self):
        """The catalogue has no identifier for a link, so the pair itself is the key: what is
        already joined — by Onisep or by a previous run — is left alone.
        """
        known = set(FormationAction.objects.values_list("formation_id", "school_id"))
        FormationAction.objects.bulk_create(
            [
                FormationAction(onisep_id=None, formation_id=formation_pk, school_id=school_pk)
                for formation_pk, school_pk in self._links - known
            ],
            batch_size=1000,
        )


def _flag(level: str) -> str:
    return "secondary" if is_secondary(level) else "higher_ed"
