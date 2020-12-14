### Description

This microservice is called ```CAPTCHA```. It provides an HTTP server accepting two routes for generate and validate a CAPTCHA

### Build

    $ docker-compose build
    
This will build a Docker image named ```cr.pedrozena.io/test/captcha:local```

### Debug inside the Docker container with Visual Studio Code

0) You must install [Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension
1) Open the Command Palette in Visual Studio Code and select "**Remote-Containers:Open Folder in container**"
2) Select the root folder for this project
3) Visual Studio Code will reopen the above folder inside the container of the microservice
4) Once Visual Studio Code is opened, you can go into Debug section and debug the code by using the configuration "**[PYTHON]: ms debug**"

### Run

This microservice need to run togheter with a support database. Corrently only PostgreSQL is supported.
The docker-compose file already provide the defenition for the support database.

You can run the ```CAPTCHA``` microservice with a preconfigured database by spinning it trough docker-compose

    $ docker-compose up captcha

You can customize the settings related to the serer host & port, as well as the supporting Database information, 
by overriding the default configuration of

    $settings.yaml

You can directly edit this file, or use Environment Variables.
In this latter case you need to upper-case each variable, separating each level with an underscore.
A usage example is provided in the docker-compose file:

```yaml
service:
  captcha:
    ...
    environment:
      DB_PASSWORD : postgres
      DB_PORT : 5432
      SERVICE_HOST : 0.0.0.0
      SERVICE_PORT : 8088
```
### Test

This microservice is provided with a test suite based on pytest

You can run the ```CAPTCHA``` microservice test by using the VSCode configured debug "**[PYTHON]: ms test**"
Alternatively, you can directly run the test with:

    $ pytest

from /workspace directory. \
Please override PYTHONPATH env variable with     

    $ /workspace/src 

to enable pytest run from command-line (you can uncomment the related option in .devcontainer.json to achieve this).

### Documentation

You can find the documentation automatically served by FastAPI (provided by Swagger) by visiting ```http://host:port/docs``` while the microservice is up & running