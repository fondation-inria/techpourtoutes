import pytest

from techpourtoutes.services.onisep_api.fetch_formation_actions import (
    FetchOnisepFormationActions,
)

DOWNLOADS = "https://api.opendata.onisep.fr/downloads"


@pytest.mark.parametrize(
    "scope,dataset_id",
    [("lycee", "605340ddc19a9"), ("superieur", "605344579a7d7")],
)
def test_each_scope_downloads_its_own_dataset(httpx_mock, scope, dataset_id):
    httpx_mock.add_response(
        url=f"{DOWNLOADS}/{dataset_id}/{dataset_id}.json",
        json=[{"action_de_formation_af_identifiant_onisep": "AF.1"}],
    )

    result = FetchOnisepFormationActions(scope=scope)

    assert result.success
    assert result.onisep_records == [{"action_de_formation_af_identifiant_onisep": "AF.1"}]
