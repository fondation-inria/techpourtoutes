import pytest

from techpourtoutes.services.onisep_api.fetch_schools import FetchOnisepSchools

DOWNLOADS = "https://api.opendata.onisep.fr/downloads"


@pytest.mark.parametrize(
    "scope,dataset_id",
    [("secondary", "5fa5816ac6a6e"), ("higher_ed", "5fa586da5c4b6")],
)
def test_each_scope_downloads_its_own_dataset(httpx_mock, scope, dataset_id):
    httpx_mock.add_response(
        url=f"{DOWNLOADS}/{dataset_id}/{dataset_id}.json", json=[{"nom": "Lycée Voltaire"}]
    )

    result = FetchOnisepSchools(scope=scope)

    assert result.success
    assert result.onisep_records == [{"nom": "Lycée Voltaire"}]
