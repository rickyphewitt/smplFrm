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
* An example compose file exists at [compose.yaml](docker/compose/compose.yaml)
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

| Name                                 | Default                            | Description                                                                                  |
|--------------------------------------|------------------------------------|----------------------------------------------------------------------------------------------|
| `SMPL_FRM_LIBRARY_DIRS`              | "<settings.py-dir>./../../library" | Comma Separated String of directory paths                                                    |
| `SMPL_FRM_IMAGE_FORMATS`             | "jpg,png"                          | Comma Separated String of directory paths                                                    |
| `SMPL_FRM_IMAGE_REFRESH_INTERVAL`    | 30000                              | How long to display an image (millis)                                                        |
| `SMPL_FRM_IMAGE_TRANSITION_INTERVAL` | 10000                              | How long to transition the image (millis)                                                    |
| `SMPL_FRM_EXTERNAL_PORT`             | 8321                               | Used in Docker when the external port differs from the server port                           |
| `SMPL_FRM_HOST`                      | localhost                          | Used when running the application on a server                                                |
| `SMPL_FRM_PROTOCOL`                  | "http://"                          | Set to "https://" for ssl                                                                    |
| `SMPL_FRM_DISPLAY_DATE`              | True                               | Display date (Month, Year) of photo. This reads the exif image data                          |
| `SMPL_FRM_FORCE_DATE_FROM_PATH`      | True                               | Use the filepath to determine date supports `YYYY/MM` 2024/12                                |
| `SMPL_FRM_DISPLAY_CLOCK`             | True                               | Display the Clock                                                                            |
| `SMPL_FRM_DISPLAY_WEATHER`           | True                               | Display the Weather. [Weather data by Open-Meteo.com](https://open-meteo.com)                |
| `SMPL_FRM_WEATHER_COORDS`            | "63.1786,-147.4661"                | Lat,Long for weather                                                                         |
| `SMPL_FRM_WEATHER_TEMP_UNIT`         | "F"                                | `F` for Fahrenheit, `C` for Celsius                                                          |
| `SMPL_FRM_WEATHER_PRECIP_UNIT`       | "in"                               | `in` for inches, `mm` for millimeters                                                        |
| `SMPL_FRM_WEATHER_WINDSPEED_UNIT`    | "mph"                              | `kmh` kilos per hour, `kn` knots, `ms` meters per second, `mph` miles per hour               |
| `SMPL_FRM_TIMEZONE`                  | "America/Los_Angeles"              | TZ Identified from [Wikipedia](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) |
| `SMPL_FRM_IMAGE_CACHE_TIMEOUT`       | "86400"                            | Seconds until the image should be removed from the cache                                     |
| `SMPL_FRM_CLEAR_CACHE_ON_BOOT`       | False                              | Clears Cache on Service Boot                                                                 |