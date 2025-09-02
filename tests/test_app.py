import pytest
from app import app

@pytest.fixture(name="client")
def app_client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_root_redirects_to_api(client):
    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "success"
    assert data["message"] == "Detection Service on Production!"
