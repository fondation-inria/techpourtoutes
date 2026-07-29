from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from techpourtoutes.models import EligibleSchool


def _record(uai, formation_id, **overrides):
    record = {
        "id": formation_id,
        "etablissement_formateur_uai": uai,
        "etablissement_gestionnaire_uai": None,
        "etablissement_lieu_formation_uai": None,
        "nom": None,
        "intitule_long": "Licence Histoire",
        "code_postal": "75013",
        "onisep_domaine_sousdomaine": None,
        "onisep_discipline": None,
        "diplome": "Licence",
        "niveau": "6 (LICENCE...)",
        "rncp_intitule": "Licence Histoire",
    }
    record.update(overrides)
    return record


def _mock_response(records, *, page=1, nombre_de_page=1):
    response = MagicMock()
    response.is_success = True
    response.json.return_value = {
        "formations": records,
        "pagination": {
            "page": page,
            "resultats_par_page": len(records),
            "nombre_de_page": nombre_de_page,
            "total": len(records),
        },
    }
    return response


def _call(*responses):
    with patch(
        "techpourtoutes.management.commands.import_apprenticeship_formations.httpx.get"
    ) as mock_get:
        mock_get.side_effect = responses
        call_command("import_apprenticeship_formations")
    return mock_get


@pytest.mark.django_db
def test_raises_when_request_fails(higher_ed_school):
    response = MagicMock()
    response.is_success = False
    response.status_code = 500
    with patch(
        "techpourtoutes.management.commands.import_apprenticeship_formations.httpx.get",
        return_value=response,
    ):
        with pytest.raises(CommandError):
            call_command("import_apprenticeship_formations")


@pytest.mark.django_db
def test_records_formation_for_known_higher_ed_school(higher_ed_school):
    _call(_mock_response([_record(higher_ed_school.uai, "f1")]))

    school = EligibleSchool.objects.get(uai=higher_ed_school.uai)
    assert school.name == higher_ed_school.display_label
    assert school.education_level == EligibleSchool.EducationLevel.SUP
    assert school.matches_digital_domain is False


@pytest.mark.django_db
def test_digital_formation_sets_matches_digital_apprenticeship_but_not_digital_domain(
    higher_ed_school,
):
    record = _record(
        higher_ed_school.uai,
        "f1",
        onisep_domaine_sousdomaine="informatique, internet/développement",
    )
    _call(_mock_response([record]))

    school = EligibleSchool.objects.get(uai=higher_ed_school.uai)
    assert school.matches_digital_apprenticeship is True
    assert school.matches_digital_domain is False


@pytest.mark.django_db
def test_non_digital_formation_does_not_set_matches_digital_domain(higher_ed_school):
    _call(_mock_response([_record(higher_ed_school.uai, "f1")]))

    school = EligibleSchool.objects.get(uai=higher_ed_school.uai)
    assert school.matches_digital_domain is False
    assert school.matches_digital_apprenticeship is False


@pytest.mark.django_db
def test_no_higher_ed_school_means_no_api_call():
    mock_get = _call()
    mock_get.assert_not_called()
    assert EligibleSchool.objects.count() == 0


@pytest.mark.django_db
def test_dedupes_formation_seen_via_multiple_uai(higher_ed_school):
    higher_ed_school.uai = "0911101X;0911102Y"
    higher_ed_school.save()
    same_record = _record("0911101X", "f1")

    _call(
        _mock_response([same_record]),
        _mock_response([same_record]),
    )

    assert EligibleSchool.objects.count() == 1


@pytest.mark.django_db
def test_rerun_is_idempotent(higher_ed_school):
    def _run():
        return _call(_mock_response([_record(higher_ed_school.uai, "f1")]))

    _run()
    _run()

    assert EligibleSchool.objects.count() == 1


@pytest.mark.django_db
def test_batches_multiple_known_uais_into_a_single_api_call(higher_ed_school):
    from techpourtoutes.models import HigherEdSchool

    other_school = HigherEdSchool.objects.create(
        full_name="Autre école",
        name="Autre",
        uai="0911999Z",
    )

    mock_get = _call(
        _mock_response([_record(higher_ed_school.uai, "f1"), _record(other_school.uai, "f2")])
    )

    assert mock_get.call_count == 1
    assert EligibleSchool.objects.filter(uai=other_school.uai).exists()
