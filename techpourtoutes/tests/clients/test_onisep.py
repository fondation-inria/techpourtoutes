from techpourtoutes.clients.onisep import OnisepClient

DATASET_URL = "https://api.opendata.onisep.fr/downloads/5fa591127f501/5fa591127f501.json"


def test_onisep_client_downloads_a_dataset_as_json(httpx_mock):
    httpx_mock.add_response(url=DATASET_URL, status_code=200, json=[{"code_nsf": "314"}])

    response = OnisepClient().download_dataset(dataset_id="5fa591127f501")

    assert response.is_success
    assert response.json() == [{"code_nsf": "314"}]
    request = httpx_mock.get_request()
    assert request.method == "GET"
    assert str(request.url) == DATASET_URL
