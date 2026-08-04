from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from techpourtoutes.models import School

RECORDS = [
    {
        "identifiant_de_l_etablissement": "0750001A",
        "nom_etablissement": "Lycée Voltaire",
        "code_postal": "75011",
    },
    {
        "identifiant_de_l_etablissement": "0690002B",
        "nom_etablissement": "Collège Jean Moulin",
        "code_postal": "69003",
    },
]


def _mock_response(records):
    response = MagicMock()
    response.is_success = True
    response.json.return_value = records
    return response


@pytest.mark.django_db
def test_import_schools_creates_rows():
    with patch("techpourtoutes.management.commands.import_schools.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(RECORDS)
        call_command("import_schools")

    assert School.objects.count() == 2
    voltaire = School.objects.get(identifier="0750001A")
    assert voltaire.name == "Lycée Voltaire"
    assert voltaire.postal_code == "75011"


@pytest.mark.django_db
def test_import_schools_populates_normalized_name():
    with patch("techpourtoutes.management.commands.import_schools.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(RECORDS)
        call_command("import_schools")

    assert School.objects.get(identifier="0750001A").name_normalized == "Lycee Voltaire"


@pytest.mark.django_db
def test_import_schools_is_idempotent_and_updates():
    updated = [{**RECORDS[0], "nom_etablissement": "Lycée Voltaire (rénové)"}]
    with patch("techpourtoutes.management.commands.import_schools.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(RECORDS)
        call_command("import_schools")
        mock_get.return_value = _mock_response(updated)
        call_command("import_schools")

    assert School.objects.count() == 2
    assert School.objects.get(identifier="0750001A").name == "Lycée Voltaire (rénové)"


@pytest.mark.django_db
def test_import_schools_deduplicates_records_with_same_identifier():
    records = [
        RECORDS[0],
        {**RECORDS[0], "nom_etablissement": "Lycée Voltaire (doublon)"},
    ]
    with patch("techpourtoutes.management.commands.import_schools.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(records)
        call_command("import_schools")

    assert School.objects.count() == 1
    assert School.objects.get(identifier="0750001A").name == "Lycée Voltaire (doublon)"


@pytest.mark.django_db
def test_import_schools_skips_records_without_identifier_or_name():
    records = [
        *RECORDS,
        {"identifiant_de_l_etablissement": "", "nom_etablissement": "Sans id", "code_postal": "1"},
        {"identifiant_de_l_etablissement": "X", "nom_etablissement": "", "code_postal": "2"},
    ]
    with patch("techpourtoutes.management.commands.import_schools.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(records)
        call_command("import_schools")

    assert School.objects.count() == 2
