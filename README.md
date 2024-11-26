# smplFrm
Digital Photoframe for displaying photos on any device that has a web browser


## Run
### Native
* After downloading this repo create a python virtual environment                                                    
  * `python -m venv local_venv`
* Activate the `local_venv`
  * . ./local_venv/bin/activate`
* Install requirements with `pip`
  * `pip install -r requirements.txt`
* Run the server
  * `python main.py`
* Browse to `http://localhost:8000`
* Add your own assets to the `assets` folder and re-run the server to display your own photos

### Docker
* Build the dockerfile
  * `docker build -t smplFrm .`
* Run the docker file exposing ports
  * `docker run -p 8000:8000 smpl_frm`
* Browse to `http://localhost:8000`
* To add your own as assets mount a local volume to the `/app/assets` folder in the image
  * `docker run -p 8000:8000 -v <local/Folder/Path>:/app/assets smpl_frm`
### Docker Compose
* An example compose file exists at [compose.yaml](./docker/compose.yaml)
* Essentially you just need to update the `SMPL_FRM_ASSET_DIRECTORIES` and mount a local volume like below
```
services:
    smpl_frm:
        build:
            context: ../
            dockerfile: docker/images/Dockerfile
        ports:
         - "8000:8000"
        environment:
            - SMPL_FRM_ASSET_DIRECTORIES=/app/library,/app/assets
            - PYTHONUNBUFFERED=1
        volumes:
            - /example/local/library/here:/app/library

```
* Then `cd` into `./docker` and run `docker-compose up -d` and browse to `http://localhost:8000`


### Environment Variables

| Name                              | Default     | Description                                                         |
|-----------------------------------|-------------|---------------------------------------------------------------------|
| `SMPL_FRM_LIBRARY_DIRECTORIES`    | "library"   | Comma Separated String of directory paths                           |
| `SMPL_FRM_TEMPLATE_DIRECTORIES`   | "templates" | Comma Separated String of directory paths                           |
| `SMPL_FRM_IMAGE_REFRESH_INTERVAL` | 30000       | How long to display an image (millis)                               |
| `SMPL_FRM_EXTERNAL_PORT`          | 8000        | Used in Docker when the external port differs from the server port  |
| `SMPL_FRM_HOST`                   | localhost   | Used when running the application on a server                       |
| `SMPL_FRM_CACHE_DIRECTORY`        | "/tmp"      | Local cache                                                         |
| `SMPL_FRM_DISPLAY_DATE`           | False       | Display date (Month, Year) of photo. This reads the exif image data |
| `SMPL_FRM_FORCE_DATE_FROM_PATH`   | True        | Use the filepath to determine date supports `YYYY/MM` 2024/12       |