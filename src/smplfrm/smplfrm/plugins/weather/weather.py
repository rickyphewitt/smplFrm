import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from django.core.cache import cache
from open_meteo import OpenMeteo
from open_meteo.models import (
    DailyParameters,
    HourlyParameters,
    TemperatureUnit,
    PrecipitationUnit,
    WindSpeedUnit,
)

from smplfrm.plugins.base import BasePlugin

logger = logging.getLogger(__name__)


class WeatherPlugin(BasePlugin):
    """Weather plugin for collecting and displaying weather data."""

    def get_tasks(self):
        from smplfrm.plugins.weather.tasks import refresh_weather

        return {"refresh_weather": refresh_weather}

    def get_beat_schedule(self):
        return {"hourly-weather": {"task": "refresh_weather", "schedule": 1800}}

    def __init__(self) -> None:
        super().__init__(name="weather", description="Weather data")
        self.redis_key = "weather"

    def configure(self):
        """Load weather settings from DB."""
        super().configure()
        s = self.get_plugin_settings()
        coords = s.get("coords", "63.1786,-147.4661").split(",")
        self.lat = coords[0].strip()
        self.long = coords[1].strip()
        self.tz = s.get("timezone", "America/Los_Angeles")
        self._determine_temp_unit(s.get("temp_unit", "F"))
        self.precip_unit = self._determine_precip_unit(s.get("precip_unit", "in"))
        self.windspeed_unit = self._determine_windspeed_unit(
            s.get("windspeed_unit", "mph")
        )

    async def collect_weather(self) -> None:
        """Collect weather forecast and persist in cache."""
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

    def create(self, data: Any) -> None:
        """Store weather data in cache."""
        expires = timedelta(days=6).total_seconds()
        cache.set(key=self.redis_key, value=data, timeout=expires)
        logger.debug(f"Persisted Weather Data: {data}")
        logger.info("Weather Synced")

    def delete(self) -> None:
        """Delete cached weather data."""
        cache.delete(self.redis_key)

    def read(self) -> Any:
        """Retrieve cached weather data."""
        return cache.get(self.redis_key)

    def get_for_display(self, now: Optional[datetime] = None) -> Dict[str, str]:
        """Get formatted weather data for display."""
        self._ensure_configured()
        if not now:
            now = datetime.now(tz=timezone.utc)

        raw_data = self.read()
        current_temp_index = self._get_current_temp_index(raw_data, now)
        logger.debug(f"Current Temp Index: {current_temp_index}")

        if current_temp_index is not None:
            current_temp_value = self._get_current_temp(raw_data, current_temp_index)
        else:
            current_temp_value = "N/A"

        daily_index = self._get_current_daily_index(raw_data, now)
        current_low_temp_value = None
        current_high_temp_value = None

        if daily_index is not None:
            try:
                current_low_temp_value = raw_data.daily.temperature_2m_min[daily_index]
                current_high_temp_value = raw_data.daily.temperature_2m_max[daily_index]
            except Exception as e:
                logger.error(f"Failed to get low/high temps: {e}")

        if not current_low_temp_value:
            current_low_temp_value = "N/A"
        if not current_high_temp_value:
            current_high_temp_value = "N/A"

        return {
            "current_temp": f"{current_temp_value} {self.temp_unit_display}",
            "current_low_temp": f"{current_low_temp_value}{self.temp_unit_display}",
            "current_high_temp": f"{current_high_temp_value}{self.temp_unit_display}",
        }

    def _get_current_temp(self, raw_data: Any, index: int) -> Any:
        try:
            return raw_data.hourly.temperature_2m[index]
        except Exception as e:
            logger.error(f"Unable to get hourly temp: {e}")
            return "N/A"

    def _get_current_daily_index(self, raw_data: Any, now: datetime) -> Optional[int]:
        try:
            daily_time = raw_data.daily.time
            for i in range(len(daily_time)):
                if (
                    daily_time[i].year == now.year
                    and daily_time[i].month == now.month
                    and daily_time[i].day == now.day
                ):
                    return i
        except Exception as e:
            logger.error(f"Unable to determine daily index: {e}")
        return None

    def _get_current_temp_index(self, raw_data: Any, now: datetime) -> Optional[int]:
        try:
            time = raw_data.hourly.time
        except Exception as e:
            logger.error(f"Failed to extract hourly time, error: {e}")
            return None

        if time:
            for i in range(len(time)):
                if (
                    time[i].year == now.year
                    and time[i].month == now.month
                    and time[i].day == now.day
                    and time[i].hour == now.hour
                ):
                    return i
        return None

    def _determine_temp_unit(self, unit_str: str) -> None:
        self.temp_unit = TemperatureUnit.FAHRENHEIT
        self.temp_unit_display = "°F"
        if unit_str == "C":
            self.temp_unit = TemperatureUnit.CELSIUS
            self.temp_unit_display = "°C"

    def _determine_precip_unit(self, unit_str: str) -> PrecipitationUnit:
        unit = PrecipitationUnit.INCHES
        if unit_str == "mm":
            unit = PrecipitationUnit.MILLIMETERS
        return unit

    def _determine_windspeed_unit(self, unit_str: str) -> WindSpeedUnit:
        unit = WindSpeedUnit.MILES_PER_HOUR
        if unit_str == "kmh":
            unit = WindSpeedUnit.KILOMETERS_PER_HOUR
        elif unit_str == "kn":
            unit = WindSpeedUnit.KNOTS
        elif unit_str == "ms":
            unit = WindSpeedUnit.METERS_PER_SECOND
        return unit
