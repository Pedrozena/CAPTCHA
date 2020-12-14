from fastapi import FastAPI, File, UploadFile, Depends, Response, status, Request
import uvicorn
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
from ut import envOverride

logger = logging.getLogger("uvicorn.error")

ImageGenerator = ImageCaptcha(width=500, height=200)

RETRY = 10



async def appDefinition(db_settings, forceDBInit=False):
    '''
    Definition of FastAPI app object and its route handler.
    forceDBInit allow to programatically start the Database creation.
    '''
    tags_metadata = [
        {
            "name": "generate",
            "description": "Generate a CAPTCHA",
        },
        {
            "name": "validate",
            "description": "Validate a CAPTCHA against the provided secret",
        },
    ]
    app = FastAPI(
        title="CAPTCHA",
        description="HTTP server for generate and validate a CAPTCHA",
        version="0.1.0",
        openapi_tags=tags_metadata,
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png", 
    )

    async def getDb(user=db_settings["user"], password=db_settings["password"], 
        database=db_settings["database"], host=db_settings["host"], port=db_settings.get("port", 5432)):
        '''
        Return a new connection to the database configured in the settings file.
        '''
        cnt = 0
        while True:
            try:
                return await asyncpg.connect(user=user, password=password,
                    database=database, host=host, port=port)
                break
            except Exception as e:
                cnt += 1
                if cnt > RETRY:
                    logger.error(str(e))
                    sys.exit(-1)
                logger.info("unable to connect to "+host+":"+str(port)+" DB (retrying "+str(cnt)+" of "+str(RETRY)+")")
                await asyncio.sleep(1)

    async def getDbDependencies():
        '''
        Return a new connection to the database as a FastAPI dependencies.
        '''
        db = await getDb()
        try:
            yield db
        finally:
            await db.close()

    async def createDb():
        '''
        Initialize the database writing the table definition.
        '''
        try:
            db = await getDb()
        except OSError as e:
            sys.exit(str(e))
        try:
            await db.execute("CREATE TABLE captcha (hash text, secret text, timestamp timestamp);")
            logger.info("Database initialized")
        except asyncpg.DuplicateTableError:
            logger.info("Database initialization skipped")
            pass

    @app.on_event("startup")
    async def startupEvent():
        '''
        Action to be performed at server startup. Initialize the database
        '''
        await createDb()
        

    @app.on_event("startup")
    @repeat_every(seconds=60*60)
    async def garbageCollector():
        '''
        Action to be performed each n seconds. It delete old instances (CAPTCHA images generated) from the database
        '''
        db = await getDb()
        async with db.transaction():
            res = await db.execute("DELETE FROM captcha WHERE timestamp < now() - interval '1 hour'")
            logger.info("Old instances cleaned from DB: "+ res)

    @app.get("/generate/", tags=["generate"], responses={
        200: {"content": {"image/png": {}}},
        503: {"description": "Support Service Unavailable, retry again later"}
    })
    async def generate(response: Response, db: asyncpg.Connection = Depends(getDbDependencies)):
        '''
        \f
        Generate a new captcha using ImageCaptcha module.
        It store in the support DB the md5 hash of the given captcha, togheter with its secret.
        '''
        cnt = 0
        while True:
            try:
                content = urllib.request.urlopen("https://random-word-api.herokuapp.com/word?number=2").read()
                break
            except urllib.error.HTTPError:
                cnt += 1
                if cnt > RETRY:
                    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                    return False
                await asyncio.sleep(0.2)
        secret = " ".join(json.loads(content.decode('utf-8')))
        img = ImageGenerator.generate(secret)
        fingerprint = hashlib.md5(img.read()).hexdigest()
        img.seek(0)
        async with db.transaction():
            await db.execute("INSERT INTO captcha VALUES('"+fingerprint+"', '"+secret+"', current_timestamp)")
        return StreamingResponse(img, media_type="image/png") 

    @app.post("/validate/", tags=["validate"], responses={
        200: {"content": {"application/json": {}}},
        404: {"description": "CAPTCHA image never generated"},
        406: {"description": "Wrong secret"}
    })
    async def validate(secret: str, response: Response, image: UploadFile = File(...), 
        db: asyncpg.Connection = Depends(getDbDependencies)):
        '''
        \f
        Validate a pre-generated captcha against the given secret.
        It check the md5 hash of the provided file
        '''
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

    @app.get("/")
    def read_root(request: Request):
        '''
        \f
        Root Handler
        '''
        return {"Description": "CAPTCHA microservice. visit "+str(request.base_url)+"docs/ for documentation"}
    
    if forceDBInit:
        await createDb()

    return app

if __name__ == "__main__":
    description = 'CAPTCHA Microservice'
    epilog = "For any information, contact pedro.zena@gmail.com"
    settings = 'Path for settings file'

    parser = argparse.ArgumentParser(description=description, prog="CAPTCHA", epilog=epilog)
    parser.add_argument('-f', '--settingsFile', type=str, nargs=1, help=settings, default=["./settings.yml"])
    args = parser.parse_args()
    with open(args.settingsFile[0], 'r') as stream:
        settings = envOverride(yaml.safe_load(stream))
    db_settings = settings.get("db", {})
    service_settings = settings.get("service", {})

    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(appDefinition(db_settings))

    uvicorn.run(app, host=service_settings["host"], port=int(service_settings["port"]), log_level="info")