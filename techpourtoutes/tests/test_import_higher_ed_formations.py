from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from techpourtoutes.models import EligibleSchool

RECORD_CPGE = {
    "ens_code_uai": "0341234A",
    "ens_statut": "public",
    "for_type": "prépa scientifique et technologique",
    "formation_for_libelle": "CPGE scientifique MPSI",
    "lieu_denseignement_ens_libelle": "Lycée avec prépa",
    "ens_code_postal": "34000",
    "for_indexation_domaine_web_onisep": "sciences/mathématiques",
}
RECORD_CPGE_HORS_CONTRAT = {
    "ens_code_uai": "0341236C",
    "ens_statut": "privé hors contrat",
    "for_type": "prépa scientifique et technologique",
    "formation_for_libelle": "CPGE scientifique MPSI",
    "lieu_denseignement_ens_libelle": "Lycée prépa hors contrat",
    "ens_code_postal": "34002",
    "for_indexation_domaine_web_onisep": "sciences/mathématiques",
}
RECORD_CPGE_NO_UAI = {
    "ens_code_uai": "",
    "ens_statut": "public",
    "for_type": "prépa scientifique et technologique",
    "formation_for_libelle": "CPGE scientifique MPSI",
    "lieu_denseignement_ens_libelle": "Lycée prépa sans UAI",
    "ens_code_postal": "34003",
    "for_indexation_domaine_web_onisep": "sciences/mathématiques",
}
RECORD_NON_CPGE_PREPA = {
    "ens_code_uai": "0341235B",
    "ens_statut": "public",
    "for_type": "prépa littéraire et artistique",
    "formation_for_libelle": "CPGE lettres",
    "lieu_denseignement_ens_libelle": "Lycée prépa lettres",
    "ens_code_postal": "34001",
    "for_indexation_domaine_web_onisep": "lettres, langues",
}


RECORD_LYCEE_BTS_RESEAU = {
    "ens_code_uai": "0341237D",
    "ens_statut": "public",
    "for_type": "brevet de technicien supérieur",
    "formation_for_libelle": "BTS services informatiques aux organisations",
    "lieu_denseignement_ens_libelle": "Lycée polyvalent Aragon-Picasso",
    "ens_code_postal": "69700",
    "for_indexation_domaine_web_onisep": "informatique, Internet/systèmes et réseaux",
}
RECORD_LYCEE_BTS_HORS_CONTRAT = {
    "ens_code_uai": "0341238E",
    "ens_statut": "privé hors contrat",
    "for_type": "brevet de technicien supérieur",
    "formation_for_libelle": "BTS services informatiques aux organisations",
    "lieu_denseignement_ens_libelle": "Lycée privé hors contrat du Numérique",
    "ens_code_postal": "69701",
    "for_indexation_domaine_web_onisep": "informatique, Internet/systèmes et réseaux",
}
RECORD_LYCEE_BTS_NON_DIGITAL = {
    "ens_code_uai": "0341239F",
    "ens_statut": "public",
    "for_type": "brevet de technicien supérieur",
    "formation_for_libelle": "BTS métiers de la mode",
    "lieu_denseignement_ens_libelle": "Lycée Voltaire",
    "ens_code_postal": "75011",
    "for_indexation_domaine_web_onisep": "mode, habillement, textile/mode",
}


def _digital_record(uai):
    return {
        "ens_code_uai": uai,
        "for_type": "master",
        "formation_for_libelle": "master informatique",
        "lieu_denseignement_ens_libelle": "École nationale supérieure d'arts et métiers",
        "ens_code_postal": "75013",
        "for_indexation_domaine_web_onisep": (
            "informatique, Internet/informatique (généralités)| sciences/mathématiques"
        ),
    }


def _non_digital_record(uai):
    return {
        "ens_code_uai": uai,
        "for_type": "licence",
        "formation_for_libelle": "licence histoire",
        "lieu_denseignement_ens_libelle": "École nationale supérieure d'arts et métiers",
        "ens_code_postal": "75013",
        "for_indexation_domaine_web_onisep": "lettres, langues, sciences humaines",
    }


def _mock_response(records):
    response = MagicMock()
    response.is_success = True
    response.json.return_value = {"total": len(records), "size": len(records), "results": records}
    return response


def _mock_login_response():
    response = MagicMock()
    response.is_success = True
    response.json.return_value = {"token": "test-token"}
    return response


def _call(records):
    with (
        patch("techpourtoutes.management.commands._onisep_dataset.httpx.post") as mock_post,
        patch("techpourtoutes.management.commands._onisep_dataset.httpx.get") as mock_get,
    ):
        mock_post.return_value = _mock_login_response()
        mock_get.return_value = _mock_response(records)
        call_command("import_higher_ed_formations")


@pytest.mark.django_db
def test_raises_when_onisep_login_fails():
    response = MagicMock()
    response.is_success = False
    response.status_code = 401
    with (
        patch(
            "techpourtoutes.management.commands._onisep_dataset.httpx.post",
            return_value=response,
        ),
        patch("techpourtoutes.management.commands._onisep_dataset.httpx.get") as mock_get,
    ):
        with pytest.raises(CommandError):
            call_command("import_higher_ed_formations")
        mock_get.assert_not_called()


@pytest.mark.django_db
def test_syncs_higher_ed_school_with_sup_level(higher_ed_school):
    _call([])

    school = EligibleSchool.objects.get(uai=higher_ed_school.uai)
    assert school.education_level == EligibleSchool.EducationLevel.SUP
    assert school.matches_digital_domain is False


@pytest.mark.django_db
def test_cpge_creates_eligible_school_even_if_uai_unknown():
    _call([RECORD_CPGE])

    school = EligibleSchool.objects.get(uai="0341234A")
    assert school.name == "Lycée avec prépa"
    assert school.education_level == EligibleSchool.EducationLevel.BOTH
    assert school.matches_digital_domain is True


@pytest.mark.django_db
def test_non_cpge_prepa_type_is_not_matched():
    _call([RECORD_NON_CPGE_PREPA])

    assert EligibleSchool.objects.count() == 0


@pytest.mark.django_db
def test_excludes_cpge_in_private_school_without_contract():
    _call([RECORD_CPGE_HORS_CONTRAT])

    assert EligibleSchool.objects.count() == 0


@pytest.mark.django_db
def test_cpge_without_uai_does_not_crash():
    _call([RECORD_CPGE_NO_UAI])

    assert EligibleSchool.objects.count() == 0


@pytest.mark.django_db
def test_lycee_hosted_bts_is_included_without_higher_ed_school_partner():
    _call([RECORD_LYCEE_BTS_RESEAU])

    school = EligibleSchool.objects.get(uai="0341237D")
    assert school.education_level == EligibleSchool.EducationLevel.BOTH
    assert school.matches_digital_domain is True


@pytest.mark.django_db
def test_lycee_hosted_bts_excludes_private_hors_contrat():
    _call([RECORD_LYCEE_BTS_HORS_CONTRAT])

    assert EligibleSchool.objects.count() == 0


@pytest.mark.django_db
def test_lycee_hosted_non_digital_formation_is_ignored():
    _call([RECORD_LYCEE_BTS_NON_DIGITAL])

    assert EligibleSchool.objects.count() == 0


@pytest.mark.django_db
def test_digital_formation_sets_matches_digital_domain_for_known_partner(higher_ed_school):
    _call([_digital_record(higher_ed_school.uai)])

    school = EligibleSchool.objects.get(uai=higher_ed_school.uai)
    assert school.education_level == EligibleSchool.EducationLevel.SUP
    assert school.matches_digital_domain is True


@pytest.mark.django_db
def test_non_digital_formation_does_not_set_matches_digital_domain(higher_ed_school):
    _call([_non_digital_record(higher_ed_school.uai)])

    school = EligibleSchool.objects.get(uai=higher_ed_school.uai)
    assert school.matches_digital_domain is False


@pytest.mark.django_db
def test_excludes_formation_for_school_not_in_higher_ed_school():
    _call([_digital_record("9999999Z")])

    assert EligibleSchool.objects.count() == 0
