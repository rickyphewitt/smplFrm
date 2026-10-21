"""Tests for weather collection and API contract."""

import asyncio
import inspect
from unittest.mock import AsyncMock, patch

from django.test import TestCase
from open_meteo import OpenMeteo
from open_meteo.models import (
    DailyParameters,
    HourlyParameters,
    TemperatureUnit,
    PrecipitationUnit,
    WindSpeedUnit,
    Forecast,
)

from smplfrm.plugins.weather.weather import WeatherPlugin


class TestCollectWeatherApiContract(TestCase):
    """Test weather collection matches the OpenMeteo.forecast signature."""

    def setUp(self):
        self.plugin = WeatherPlugin()
        self.plugin.configure()

    @patch("smplfrm.plugins.weather.weather.OpenMeteo")
    def test_collect_weather_request_matches_library_signature(
        self, mock_open_meteo_class
    ):
        """forecast() is called only with arguments the library accepts."""
        mock_instance = AsyncMock()
        # Use a real minimal Forecast instead of MagicMock for pickling
        forecast_json = '{"latitude":63.0,"longitude":-147.0,"elevation":836.0,"generationtime_ms":0.1,"utc_offset_seconds":0,"timezone":"GMT","timezone_abbreviation":"GMT"}'
        mock_forecast = Forecast.from_json(forecast_json)
        mock_instance.forecast = AsyncMock(return_value=mock_forecast)
        mock_open_meteo_class.return_value.__aenter__.return_value = mock_instance

        asyncio.run(self.plugin.collect_weather())

        mock_instance.forecast.assert_called_once()
        kwargs = mock_instance.forecast.call_args.kwargs

        # Must bind to the actual library signature
        sig = inspect.signature(OpenMeteo.forecast)
        try:
            # Exclude 'self' for binding
            sig.bind_partial(None, **kwargs)  # None for self
        except TypeError as e:
            self.fail(f"forecast() call does not match library signature: {e}")

        # Must request the required parameters
        self.assertEqual(
            set(kwargs.get("daily", [])),
            {
                DailyParameters.SUNRISE,
                DailyParameters.SUNSET,
                DailyParameters.TEMPERATURE_2M_MAX,
                DailyParameters.TEMPERATURE_2M_MIN,
            },
        )
        self.assertEqual(
            set(kwargs.get("hourly", [])),
            {
                HourlyParameters.TEMPERATURE_2M,
                HourlyParameters.RELATIVE_HUMIDITY_2M,
            },
        )

    @patch("smplfrm.plugins.weather.weather.OpenMeteo")
    def test_collect_weather_persists_forecast(self, mock_open_meteo_class):
        """The collected forecast is persisted and readable from the cache."""
        mock_instance = AsyncMock()
        # Use a real minimal Forecast
        forecast_json = '{"latitude":63.0,"longitude":-147.0,"elevation":836.0,"generationtime_ms":0.1,"utc_offset_seconds":0,"timezone":"GMT","timezone_abbreviation":"GMT"}'
        mock_forecast = Forecast.from_json(forecast_json)
        mock_instance.forecast = AsyncMock(return_value=mock_forecast)
        mock_open_meteo_class.return_value.__aenter__.return_value = mock_instance

        asyncio.run(self.plugin.collect_weather())

        stored = self.plugin.read()
        self.assertIsNotNone(stored)
        self.assertEqual(stored.latitude, 63.0)


class TestUnitMapping(TestCase):
    """Test unit enum wire values match Open-Meteo API."""

    def setUp(self):
        self.plugin = WeatherPlugin()

    def test_temp_unit_mapping_fahrenheit(self):
        """Fahrenheit setting produces correct enum with wire value 'fahrenheit'."""
        self.plugin._determine_temp_unit("F")
        self.assertEqual(self.plugin.temp_unit, TemperatureUnit.FAHRENHEIT)
        self.assertEqual(self.plugin.temp_unit.value, "fahrenheit")

    def test_temp_unit_mapping_celsius(self):
        """Celsius setting produces correct enum with wire value 'celsius'."""
        self.plugin._determine_temp_unit("C")
        self.assertEqual(self.plugin.temp_unit, TemperatureUnit.CELSIUS)
        self.assertEqual(self.plugin.temp_unit.value, "celsius")

    def test_temp_unit_mapping_default(self):
        """Missing or unknown temp unit falls back to Fahrenheit."""
        self.plugin._determine_temp_unit("")
        self.assertEqual(self.plugin.temp_unit, TemperatureUnit.FAHRENHEIT)
        self.plugin._determine_temp_unit(None)
        self.assertEqual(self.plugin.temp_unit, TemperatureUnit.FAHRENHEIT)

    def test_windspeed_unit_mapping_mph(self):
        """mph setting produces enum with wire value 'mph'."""
        unit = self.plugin._determine_windspeed_unit("mph")
        self.assertEqual(unit, WindSpeedUnit.MILES_PER_HOUR)
        self.assertEqual(unit.value, "mph")

    def test_windspeed_unit_mapping_kmh(self):
        """kmh setting produces enum with wire value 'kmh'."""
        unit = self.plugin._determine_windspeed_unit("kmh")
        self.assertEqual(unit, WindSpeedUnit.KILOMETERS_PER_HOUR)
        self.assertEqual(unit.value, "kmh")

    def test_windspeed_unit_mapping_kn(self):
        """kn setting produces enum with wire value 'kn'."""
        unit = self.plugin._determine_windspeed_unit("kn")
        self.assertEqual(unit, WindSpeedUnit.KNOTS)
        self.assertEqual(unit.value, "kn")

    def test_windspeed_unit_mapping_ms(self):
        """ms setting produces enum with wire value 'ms'."""
        unit = self.plugin._determine_windspeed_unit("ms")
        self.assertEqual(unit, WindSpeedUnit.METERS_PER_SECOND)
        self.assertEqual(unit.value, "ms")

    def test_windspeed_unit_mapping_default(self):
        """Missing or unknown windspeed unit falls back to mph."""
        unit = self.plugin._determine_windspeed_unit("")
        self.assertEqual(unit, WindSpeedUnit.MILES_PER_HOUR)
        unit = self.plugin._determine_windspeed_unit(None)
        self.assertEqual(unit, WindSpeedUnit.MILES_PER_HOUR)

    def test_precip_unit_mapping_inches(self):
        """in setting produces enum with wire value 'inch'."""
        unit = self.plugin._determine_precip_unit("in")
        self.assertEqual(unit, PrecipitationUnit.INCHES)
        self.assertEqual(unit.value, "inch")

    def test_precip_unit_mapping_millimeters(self):
        """mm setting produces enum with wire value 'mm'."""
        unit = self.plugin._determine_precip_unit("mm")
        self.assertEqual(unit, PrecipitationUnit.MILLIMETERS)
        self.assertEqual(unit.value, "mm")

    def test_precip_unit_mapping_default(self):
        """Missing or unknown precip unit falls back to inches."""
        unit = self.plugin._determine_precip_unit("")
        self.assertEqual(unit, PrecipitationUnit.INCHES)
        unit = self.plugin._determine_precip_unit(None)
        self.assertEqual(unit, PrecipitationUnit.INCHES)
