from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from techpourtoutes.models import EligibleSchool

RECORD_CIEL = {
    "ens_code_uai": "0341523W",
    "ens_statut": "privé sous contrat",
    "lieu_denseignement_ens_libelle": "Lycée privé polyvalent Saint-Joseph",
    "ens_code_postal": "34202",
    "formation_for_libelle": "bac pro Cybersécurité, informatique et réseaux, électronique (CIEL)",
}
RECORD_STMG = {
    "ens_code_uai": "0750001A",
    "ens_statut": "public",
    "lieu_denseignement_ens_libelle": "Lycée Voltaire",
    "ens_code_postal": "75011",
    "formation_for_libelle": "bac techno STMG",
}
RECORD_UNMATCHED = {
    "ens_code_uai": "0690002B",
    "ens_statut": "public",
    "lieu_denseignement_ens_libelle": "Collège Jean Moulin",
    "ens_code_postal": "69003",
    "formation_for_libelle": "classe de 1re générale",
}
RECORD_HORS_CONTRAT = {
    "ens_code_uai": "0123456X",
    "ens_statut": "privé hors contrat",
    "lieu_denseignement_ens_libelle": "Lycée hors contrat",
    "ens_code_postal": "13001",
    "formation_for_libelle": "bac pro CIEL",
}


def _mock_response(records):
    response = MagicMock()
    response.is_success = True
    response.json.return_value = {"total": len(records), "size": len(records), "results": records}
    return response


def _call(records):
    with patch("techpourtoutes.management.commands._onisep_dataset.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(records)
        call_command("import_lycee_formations")


@pytest.mark.django_db
def test_creates_eligible_school_with_non_sup_level():
    _call([RECORD_CIEL])

    school = EligibleSchool.objects.get(uai="0341523W")
    assert school.name == "Lycée privé polyvalent Saint-Joseph"
    assert school.postal_code == "34202"
    assert school.education_level == EligibleSchool.EducationLevel.NON_SUP
    assert school.matches_digital_domain is True


@pytest.mark.django_db
def test_matches_stmg_bac_techno():
    _call([RECORD_STMG])

    assert EligibleSchool.objects.filter(uai="0750001A").exists()


@pytest.mark.django_db
def test_skips_unmatched_formation():
    _call([RECORD_UNMATCHED])

    assert EligibleSchool.objects.count() == 0


@pytest.mark.django_db
def test_excludes_private_hors_contrat():
    _call([RECORD_HORS_CONTRAT])

    assert EligibleSchool.objects.count() == 0


@pytest.mark.django_db
def test_rerun_is_idempotent():
    _call([RECORD_CIEL])
    _call([RECORD_CIEL])

    assert EligibleSchool.objects.count() == 1
