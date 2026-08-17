from techpourtoutes.services.onisep_api.fetch_formations import FetchOnisepFormations

DATASET_URL = "https://api.opendata.onisep.fr/downloads/5fa591127f501/5fa591127f501.json"


def test_formations_have_a_single_dataset(httpx_mock):
    httpx_mock.add_response(url=DATASET_URL, json=[{"libelle_formation_principal": "CAP Cuisine"}])

    result = FetchOnisepFormations()

    assert result.success
    assert result.onisep_records == [{"libelle_formation_principal": "CAP Cuisine"}]
