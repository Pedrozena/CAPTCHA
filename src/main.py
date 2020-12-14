from fastapi import FastAPI, File, UploadFile, Depends, Response, status
import uvicorn
import os
import yaml
import argparse
import asyncpg
import asyncio
import sys
import uvicorn
import urllib.request
import json
import hashlib 
import logging
from time import time 
from captcha.image import ImageCaptcha
from fastapi.responses import StreamingResponse
from fastapi_utils.tasks import repeat_every

logger = logging.getLogger("uvicorn.error")

ImageGenerator = ImageCaptcha(width=500, height=200)

async def appDefinition(db_settings):
    app = FastAPI()

    async def getDb(user=db_settings["user"], password=db_settings["password"], 
        database=db_settings["database"], host=db_settings["host"]):
        return await asyncpg.connect(user=user, password=password,
            database=database, host=host)

    async def getDbDependencies():
        db = await getDb()
        try:
            yield db
        finally:
            await db.close()

    @app.get("/generate/")
    async def generate(response: Response, db: asyncpg.Connection = Depends(getDbDependencies)):
        cnt = 0
        while True:
            try:
                content = urllib.request.urlopen("https://random-word-api.herokuapp.com/word?number=2").read()
                break
            except urllib.error.HTTPError:
                cnt += 1
                if cnt > 10:
                    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                    return False
                asyncio.sleep(0.2)
        secret = " ".join(json.loads(content.decode('utf-8')))
        img = ImageGenerator.generate(secret)
        fingerprint = hashlib.md5(img.read()).hexdigest()
        img.seek(0)
        async with db.transaction():
            await db.execute("INSERT INTO captcha VALUES('"+fingerprint+"', '"+secret+"', current_timestamp)")
        return StreamingResponse(img, media_type="image/png") 

    @app.post("/validate/")
    async def validate(secret: str, response: Response, image: UploadFile = File(...), 
        db: asyncpg.Connection = Depends(getDbDependencies)):
        fingerprint = hashlib.md5(await image.read()).hexdigest()
        async with db.transaction():
            res = await db.fetchrow("SELECT secret FROM captcha WHERE hash = '"+fingerprint+"'")
            if res is None:
                response.status_code = status.HTTP_404_NOT_FOUND
                return False
            if secret != res[0]:
                response.status_code = status.HTTP_406_NOT_ACCEPTABLE
                return False
            if secret == res[0]:
                return True

    @app.on_event("startup")
    async def startupEvent():
        try:
            db = await getDb()
        except OSError as e:
            sys.exit(str(e))
        try:
            await db.execute("CREATE TABLE captcha (hash text, secret text, timestamp timestamp);")
            logger.info("Database created")
        except asyncpg.DuplicateTableError:
            logger.info("Database creation skipped")
            pass

    @app.on_event("startup")
    @repeat_every(seconds=60*60)
    async def garbageCollector():
        db = await getDb()
        async with db.transaction():
            res = await db.execute("DELETE FROM captcha WHERE timestamp < now() - interval '1 hour'")
            logger.info("Old instances cleaned from DB: "+ res)
    
    return app

if __name__ == "__main__":
    description = 'CAPTCHA Microservice'
    epilog = "For any information, contact pedro.zena@gmail.com"
    settings = 'Path for settings file'

    parser = argparse.ArgumentParser(description=description, prog="CAPTCHA", epilog=epilog)
    parser.add_argument('-f', '--settingsFile', type=str, nargs=1, help=settings, default=["./settings.yml"])
    args = parser.parse_args()
    with open(args.settingsFile[0], 'r') as stream:
        settings = yaml.safe_load(stream)
    db_settings = settings.get("db", {})
    service_settings = settings.get("service", {})

    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(appDefinition(db_settings))

    uvicorn.run(app, host=service_settings["host"], port=service_settings["port"], log_level="info")