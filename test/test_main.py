from fastapi.testclient import TestClient
from .. src.main import appDefinition
import asyncio


loop = asyncio.get_event_loop()
app = loop.run_until_complete(appDefinition({
    "user" : "postgres",
    "password" : "postgres",
    "host" : "postgres",
    "database" : "postgres"
}))

client = TestClient(app)

def test_get_generate():
    response = client.get("/generate")
    assert response.status_code == 200
    assert type(response.content) is bytes
    assert response.headers == {"content-type": "image/png"}
