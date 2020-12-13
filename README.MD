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