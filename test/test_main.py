from fastapi.testclient import TestClient
from src.main import appDefinition
import asyncio
import pg8000
import hashlib
from captcha.image import ImageCaptcha

ImageGenerator = ImageCaptcha(width=500, height=200)

test_db = {
    "user" : "postgres",
    "password" : "postgres",
    "host" : "postgres",
    "database" : "postgres",
    "port": "5432"
}


loop = asyncio.get_event_loop()
app = loop.run_until_complete(appDefinition(test_db))

client = TestClient(app)

def test_get_home():
    response = client.get("/")
    assert response.status_code == 200

def test_get_generate():
    response = client.get("/generate")
    assert response.status_code == 200
    assert type(response.content) is bytes
    assert response.headers == {"content-type": "image/png"}

def test_post_validate_invalid():
    response = client.post("/validate/?secret=test", files={
        "image": ImageGenerator.generate("test2").read()
    })
    assert response.status_code == 404

def test_post_validate_mock():
    db = pg8000.connect(**test_db)
    img = ImageGenerator.generate("test")
    fingerprint = hashlib.md5(img.read()).hexdigest()
    db.run("INSERT INTO captcha VALUES('"+fingerprint+"', 'test', current_timestamp)")
    db.commit()
    img.seek(0)
    response = client.post("/validate/?secret=test", files={
        "image": img.read()
    })
    assert response.status_code == 200
    img.seek(0)
    response = client.post("/validate/?secret=wrong", files={
        "image": img.read()
    })
    assert response.status_code == 406