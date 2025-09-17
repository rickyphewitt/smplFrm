import asyncio

from open_meteo import OpenMeteo
from open_meteo.models import (
    DailyParameters,
    HourlyParameters,
    TemperatureUnit,
    PrecipitationUnit,
    WindSpeedUnit,
)
from django.core.cache import cache
from datetime import datetime, timedelta, timezone
import logging

from smplfrm.settings import (
    SMPL_FRM_WEATHER_COORDS,
    SMPL_FRM_TIMEZONE,
    SMPL_FRM_WEATHER_TEMP_UNIT,
    SMPL_FRM_WEATHER_PRECIP_UNIT,
    SMPL_FRM_WEATHER_WINDSPEED_UNIT,
)

logger = logging.getLogger(__name__)


class WeatherService(object):

    def __init__(self):
        self.redis_key = "weather"
        coords = SMPL_FRM_WEATHER_COORDS.split(",")
        self.lat = coords[0].strip()
        self.long = coords[1].strip()
        self.tz = SMPL_FRM_TIMEZONE
        self.__determine_temp_unit()
        self.precip_unit = self.__determine_precip_unit()
        self.windspeed_unit = self.__determine_windspeed_unit()

    async def collect_weather(self):
        """Collect the weather and then persist in redis for fetching"""
        async with OpenMeteo() as open_meteo:
            forecast = await open_meteo.forecast(
                latitude=self.lat,
                longitude=self.long,
                current_weather=True,
                daily=[
                    DailyParameters.SUNRISE,
                    DailyParameters.SUNSET,
                    DailyParameters.TEMPERATURE_2M_MAX,
                    DailyParameters.TEMPERATURE_2M_MIN,
                ],
                hourly=[
                    HourlyParameters.TEMPERATURE_2M,
                    HourlyParameters.RELATIVE_HUMIDITY_2M,
                ],
                temperature_unit=self.temp_unit,
                wind_speed_unit=self.windspeed_unit,
            )
            self.create(forecast)

    def create(self, data):
        expires = timedelta(days=6).total_seconds()
        cache.set(key=self.redis_key, value=data, timeout=expires)
        logger.debug("Persisted Weather Data: " + str(data))
        print("Weather Synced")

    def delete(self):
        cache.delete(self.redis_key)

    def read(self):
        return cache.get(self.redis_key)

    def get_for_display(self, now=None):
        if not now:
            # or ease of unit testing, should mock later
            now = datetime.now(tz=timezone.utc)

        raw_data = self.read()
        current_temp_index = self.__get_current_temp_index(raw_data, now)
        logger.debug(f"Current Temp Index: {current_temp_index}")
        if current_temp_index is not None:
            current_temp_value = self.__get_current_temp(raw_data, current_temp_index)
        else:
            current_temp_value = "N/A"

        daily_index = self.__get_current_daily_index(raw_data, now)
        current_low_temp_value = None
        current_high_temp_value = None
        if daily_index is not None:
            try:
                current_low_temp_value = raw_data.daily.temperature_2m_min[daily_index]
                current_high_temp_value = raw_data.daily.temperature_2m_max[daily_index]
            except Exception as e:
                logger.error(f"Failed to get low/high temps: {str(e)}")
                pass

        if not current_low_temp_value:
            current_low_temp_value = "N/A"
        if not current_high_temp_value:
            current_high_temp_value = "N/A"

        return {
            "current_temp": f"{current_temp_value} {self.temp_unit_display}",
            "current_low_temp": f"{current_low_temp_value}{self.temp_unit_display}",
            "current_high_temp": f"{current_high_temp_value}{self.temp_unit_display}",
        }

    def __get_current_temp(self, raw_data, index):
        try:
            return raw_data.hourly.temperature_2m[index]
        except Exception as e:
            logger.error(f"Unable to get hourly temp: {str(e)}")
            return "N/A"

    def __get_current_daily_index(self, raw_data, now):
        try:
            daily_time = raw_data.daily.time
            for i in range(len(daily_time)):
                if (
                    daily_time[i].year == now.year
                    and daily_time[i].month == now.month
                    and daily_time[i].day == now.day
                ):
                    index_of_temp = i
                    return index_of_temp
                else:
                    continue
        except Exception as e:
            logger.error(f"Unable to determine daily index: {str(e)}")
            return None

    def __get_current_temp_index(self, raw_data, now):

        time = None

        try:
            time = raw_data.hourly.time
        except Exception as e:
            logger.error(f"Failed to extract hourly time, error: {str(e)}")

        if time:
            now_year = now.year
            now_month = now.month
            now_day = now.day
            now_hour = now.hour

            for i in range(len(time)):
                if (
                    time[i].year == now_year
                    and time[i].month == now_month
                    and time[i].day == now_day
                    and time[i].hour == now_hour
                ):
                    return i
        else:
            return None

    ### private methods
    def __determine_temp_unit(self):
        self.temp_unit = TemperatureUnit.FAHRENHEIT
        self.temp_unit_display = "°F"
        if SMPL_FRM_WEATHER_TEMP_UNIT == "C":
            self.temp_unit = TemperatureUnit.CELSIUS
            self.temp_unit_diplay = "°C"

    def __determine_precip_unit(self):
        unit = PrecipitationUnit.INCHES
        if SMPL_FRM_WEATHER_PRECIP_UNIT == "mm":
            unit = PrecipitationUnit.MILLIMETERS

        return unit

    def __determine_windspeed_unit(self):
        unit = WindSpeedUnit.MILES_PER_HOUR
        if SMPL_FRM_WEATHER_WINDSPEED_UNIT == "kmh":
            unit = WindSpeedUnit.KILOMETERS_PER_HOUR
        elif SMPL_FRM_WEATHER_WINDSPEED_UNIT == "kn":
            unit = WindSpeedUnit.KNOTS
        elif SMPL_FRM_WEATHER_WINDSPEED_UNIT == "ms":
            unit = WindSpeedUnit.METERS_PER_SECOND

        return unit
