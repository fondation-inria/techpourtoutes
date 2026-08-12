import pytest

from techpourtoutes.models import Formation
from techpourtoutes.models.level import Level
from techpourtoutes.services.formation.upsert_formations import UpsertFormations

pytestmark = pytest.mark.django_db


def test_import_maps_every_kept_column(formation_record):
    result = UpsertFormations(records=[formation_record()])

    assert result.success
    formation = Formation.objects.get(onisep_id="9701")
    assert formation.code_nsf == "314"
    assert formation.code_scolarite == "46E31401"
    assert formation.type_acronym == ""
    assert formation.type_name == "formation d'école spécialisée"
    assert formation.name == "Assistant de comptabilité"
    assert formation.name_normalized == "Assistant de comptabilite"
    assert formation.acronym == ""
    assert formation.duration_in_years == 1
    assert formation.exit_level == Level.TERMINALE
    assert formation.code_rncp == "38506"
    assert formation.certification_level == "4"
    assert formation.certification_level_name == "niveau 4"


def test_import_reads_a_level_beyond_the_beneficiary_funnel(formation_record):
    UpsertFormations(records=[formation_record(niveau_de_sortie_indicatif="bac + 6")])

    assert Formation.objects.get(onisep_id="9701").exit_level == Level.BAC_6


def test_an_unspecified_level_stays_empty(formation_record):
    UpsertFormations(records=[formation_record(niveau_de_sortie_indicatif="non renseigné")])

    assert Formation.objects.get(onisep_id="9701").exit_level == ""


def test_import_updates_an_existing_formation_rather_than_duplicating_it(formation_record):
    UpsertFormations(records=[formation_record()])
    UpsertFormations(records=[formation_record(duree="3 ans")])

    assert Formation.objects.count() == 1
    assert Formation.objects.get(onisep_id="9701").duration_in_years == 3


def test_records_repeated_in_one_file_are_deduplicated(formation_record):
    UpsertFormations(
        records=[formation_record(), formation_record(libelle_formation_principal="La dernière")]
    )

    assert Formation.objects.count() == 1
    assert Formation.objects.get(onisep_id="9701").name == "La dernière"


def test_import_capitalizes_the_name_without_lowering_the_rest(formation_record):
    UpsertFormations(
        records=[
            formation_record(libelle_formation_principal="diplôme d'État d'auxiliaire de vie")
        ]
    )

    assert Formation.objects.get(onisep_id="9701").name == "Diplôme d'État d'auxiliaire de vie"


def test_a_record_without_an_identifier_is_skipped(formation_record):
    UpsertFormations(records=[formation_record(url_et_id_onisep=""), formation_record()])

    assert Formation.objects.count() == 1
