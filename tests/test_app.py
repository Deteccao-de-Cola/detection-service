import pytest
from app import app

@pytest.fixture(name="client")
def app_client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_root_redirects_to_swagger(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/swagger-ui"
