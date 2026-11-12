import html
import re
from datetime import datetime

import nh3
from django.db import transaction
from django.utils import timezone

from techpourtoutes.models import JobPosting
from techpourtoutes.services.base import BaseService
from techpourtoutes.utils.job_posting import (
    DESCRIPTION_ATTRIBUTES,
    DESCRIPTION_TAGS,
    city_name,
    upsert_in_batches,
    with_line_breaks,
)
from techpourtoutes.utils.naf import naf_label
from techpourtoutes.utils.territories import department_code

# The Apec functions we import: design, research and development, IT.
FUNCTION_DOMAINS = {
    "02B": JobPosting.Domain.CREATION,
    "04A": JobPosting.Domain.CONCEPTION_RECHERCHE,
    "04B": JobPosting.Domain.DIRECTION_RECHERCHE_DEVELOPPEMENT,
    "04D": JobPosting.Domain.PROJETS_SCIENTIFIQUES_TECHNIQUES,
    "04E": JobPosting.Domain.TEST_ESSAI_VALIDATION_EXPERTISE,
    "06A": JobPosting.Domain.INFORMATIQUE,
    "06B": JobPosting.Domain.EXPLOITATION_MAINTENANCE,
    "06C": JobPosting.Domain.INFORMATIQUE_DE_GESTION,
    "06D": JobPosting.Domain.INFORMATIQUE_INDUSTRIELLE,
    "06E": JobPosting.Domain.DEVELOPPEMENT,
    "06F": JobPosting.Domain.MAITRISE_D_OUVRAGE,
    "06G": JobPosting.Domain.SYSTEMES_ET_RESEAUX,
}
# Up to three years: past that, an offer no longer suits a first job. A level Apec would add or
# rename is left out until we decide where it belongs.
EXPERIENCE_LEVELS = {
    "Aucune expérience exigée",
    "Tous niveaux d'expérience acceptés",
    "Minimum 1 an",
    "Minimum 2 ans",
    "Minimum 3 ans",
}

CONTRACT_TYPES = {
    "CDI": JobPosting.ContractType.CDI,
    "CDD": JobPosting.ContractType.CDD,
    "Mission d'intérim": JobPosting.ContractType.INTERIM,
    "CDD - Alternance - Contrat d'apprentissage": JobPosting.ContractType.APPRENTICESHIP,
    "CDI - Alternance - Contrat d'apprentissage": JobPosting.ContractType.APPRENTICESHIP,
    "CDD - Alternance - Contrat de professionnalisation": (
        JobPosting.ContractType.PROFESSIONALIZATION
    ),
}

# Apec opens each section of an offer with a paragraph titled after it. The company's section is
# headed by its name.
SECTION_HEADINGS = {
    "description_offre": "Détail du poste",
    "profil": "Profil recherché",
}
SECTION = re.compile(r'<p title="(description_offre|profil|presentation_entreprise)">')

# The export only gives the logos' path.
LOGO_BASE_URL = "https://www.apec.fr/files/live/mounts/images"

NOTHING_TO_KEEP_MESSAGE = (
    "L'export Apec ne contient aucune offre à importer : les offres en base sont conservées."
)

MAPPED_FIELDS = [
    "title",
    "company_name",
    "description",
    "postal_code",
    "cog_code",
    "department_code",
    "city",
    "domains",
    "duration_months",
    "company_logo",
    "category",
    "contract_type",
    "experience_level",
    "salary",
    "sector",
    "published_at",
    "source_updated_at",
    "url",
]


class UpsertApecJobPostings(BaseService):
    """Mirror the Apec export: what it lists is created or updated, what it no longer lists is
    deleted.

    An offer is skipped when its function or its experience level is not one we follow. An
    export left with no offer to keep is refused: more likely Apec renamed a tag or its codes
    than withdrew every offer.
    """

    @transaction.atomic
    def perform(self, *, records) -> None:
        postings = (
            self._posting(record)
            for record in records
            if record["JOB_fonction"] in FUNCTION_DOMAINS
            and record.get("Niveau_experience") in EXPERIENCE_LEVELS
        )
        kept = upsert_in_batches(postings, update_fields=MAPPED_FIELDS)
        if not kept:
            self.fail(NOTHING_TO_KEEP_MESSAGE)
        JobPosting.all_objects.filter(source=JobPosting.Source.APEC).exclude(
            external_id__in=kept
        ).delete()

    def _posting(self, record):
        months = record.get("Duree_contrat")
        logo = record.get("Logo_entreprise")
        company_name = _plain(record["Nom_entreprise"])
        return JobPosting(
            source=JobPosting.Source.APEC,
            external_id=record["Reference_apec"],
            title=_plain(record["Intitule"]),
            company_name=company_name,
            description=_description(record["Texte_offre"], company_name),
            cog_code=record["COG_lieu"],
            department_code=department_code(record["COG_lieu"], ""),
            city=city_name(_plain(record["Libelle_lieu"])),
            domains=[FUNCTION_DOMAINS[record["JOB_fonction"]]],
            duration_months=int(months) if months else None,
            company_logo=f"{LOGO_BASE_URL}{logo}" if logo else "",
            category=_category(record),
            contract_type=CONTRACT_TYPES.get(record["Type_contrat"], ""),
            experience_level=record["Niveau_experience"],
            salary=_plain(record.get("Salaire_affiche", "")),
            sector=naf_label(record.get("NAF_secteur")),
            published_at=timezone.make_aware(
                datetime.strptime(record["Date_parution"], "%d/%m/%Y %H:%M:%S")
            ),
            url=record["URL"],
        )


def _plain(text):
    """Some company names come HTML-escaped (`M&amp;J`), some titles with doubled spaces."""
    return " ".join(html.unescape(text).split())


def _description(text, company_name):
    """Each titled paragraph is headed by its title. Most hold no text, only the paragraphs
    following: those come out of nh3 empty, and are dropped like the others."""
    headings = {**SECTION_HEADINGS, "presentation_entreprise": company_name}
    with_headings = SECTION.sub(
        lambda section: f"<h3>{html.escape(headings[section[1]])}</h3><p>", text
    )
    cleaned = nh3.clean(
        with_headings,
        tags=DESCRIPTION_TAGS,
        # nh3 keeps `title` on every tag unless told otherwise, and Apec labels its sections
        # `title="profil"`: an unknown one would show as a tooltip.
        attributes={**DESCRIPTION_ATTRIBUTES, "*": set()},
    )
    return with_line_breaks(cleaned.replace("<p></p>", ""))


def _category(record):
    contract = record["Type_contrat"]
    if contract == "Stage":
        return JobPosting.Category.HIGHER_ED_INTERNSHIP
    if "Alternance" in contract:
        return JobPosting.Category.APPRENTICESHIP
    return JobPosting.Category.FIRST_JOB
