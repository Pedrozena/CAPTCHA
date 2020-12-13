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
from datetime import datetime
from fastapi.logger import logger
from captcha.image import ImageCaptcha
from fastapi.responses import StreamingResponse

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
    async def generate(response: Response, db: asyncpg.pool = Depends(getDbDependencies)):
        cnt = 0
        while True:
            try:
                content = urllib.request.urlopen("https://random-word-api.herokuapp.com/word?number=2").read()
                break
            except urllib.error.HTTPError:
                cnt += 1
                if cnt > 20:
                    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                    return False
                asyncio.sleep(0.2)
        secret = " ".join(json.loads(content.decode('utf-8')))
        img = ImageGenerator.generate(secret)
        fingerprint = hashlib.md5(img.read()).hexdigest()
        print(fingerprint)
        img.seek(0)
        async with db.transaction():
            dt = datetime.now()
            await db.execute("INSERT INTO captcha VALUES('"+fingerprint+"', '"+secret+"', current_timestamp)")
        return StreamingResponse(img, media_type="image/png") 

    @app.post("/validate/")
    async def validate(secret: str, response: Response, image: UploadFile = File(...), 
        db: asyncpg.pool = Depends(getDbDependencies)):
        fingerprint = hashlib.md5(await image.read()).hexdigest()
        async with db.transaction():
            res = await db.fetchrow("SELECT secret FROM captcha WHERE hash = '"+fingerprint+"'")
            if secret == res[0]:
                return True
            else:
                response.status_code = status.HTTP_406_NOT_ACCEPTABLE
                return False

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