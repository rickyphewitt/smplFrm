"""Tests for weather display data formatting."""

from datetime import datetime, timezone

from django.test import TestCase
from open_meteo.models import Forecast

from smplfrm.plugins.weather.weather import WeatherPlugin


class TestWeatherDisplay(TestCase):
    """Test weather display data extraction and formatting."""

    def setUp(self):
        self.service = WeatherPlugin()
        self.service.configure()
        self.api_data = self._build_forecast_fixture()

    def test_create_display_data(self):
        """Display data extracts the current hour and today's low/high."""
        self.service.create(self.api_data)
        data = self.service.read()
        self.assertEqual(self.api_data, data)

        test_now = datetime(2025, 2, 13, 5, 0, 0, tzinfo=timezone.utc)
        display_data = self.service.get_for_display(now=test_now)

        self.assertEqual(display_data["temperature"], "7.1")
        self.assertEqual(display_data["temperature_scale"], "F")
        self.assertEqual(display_data["daily_low"], "-5.3")
        self.assertEqual(display_data["daily_low_scale"], "F")
        self.assertEqual(display_data["daily_high"], "14.4")
        self.assertEqual(display_data["daily_high_scale"], "F")

    def test_none_hourly_temperature_displays_na(self):
        """A null hourly temperature displays as 'N/A'."""
        forecast_json = """{
          "latitude": 63.0, "longitude": -147.375, "elevation": 836.0,
          "generationtime_ms": 0.09, "utc_offset_seconds": 0,
          "timezone": "GMT", "timezone_abbreviation": "GMT",
          "hourly_units": {"time": "iso8601", "temperature_2m": "°F"},
          "hourly": {
            "time": ["2025-02-13T05:00"],
            "temperature_2m": [null]
          },
          "daily_units": {"time": "iso8601", "temperature_2m_max": "°F", "temperature_2m_min": "°F"},
          "daily": {
            "time": ["2025-02-13"],
            "temperature_2m_max": [14.4],
            "temperature_2m_min": [-5.3]
          }
        }"""
        forecast = Forecast.from_json(forecast_json)
        self.service.create(forecast)

        test_now = datetime(2025, 2, 13, 5, 0, 0, tzinfo=timezone.utc)
        display_data = self.service.get_for_display(now=test_now)

        self.assertEqual(display_data["temperature"], "N/A")
        self.assertEqual(display_data["daily_low"], "-5.3")
        self.assertEqual(display_data["daily_high"], "14.4")

    def test_none_daily_extremes_display_na(self):
        """Null daily min/max temperatures display as 'N/A'."""
        forecast_json = """{
          "latitude": 63.0, "longitude": -147.375, "elevation": 836.0,
          "generationtime_ms": 0.09, "utc_offset_seconds": 0,
          "timezone": "GMT", "timezone_abbreviation": "GMT",
          "hourly_units": {"time": "iso8601", "temperature_2m": "°F"},
          "hourly": {
            "time": ["2025-02-13T05:00"],
            "temperature_2m": [7.1]
          },
          "daily_units": {"time": "iso8601", "temperature_2m_max": "°F", "temperature_2m_min": "°F"},
          "daily": {
            "time": ["2025-02-13"],
            "temperature_2m_max": [null],
            "temperature_2m_min": [null]
          }
        }"""
        forecast = Forecast.from_json(forecast_json)
        self.service.create(forecast)

        test_now = datetime(2025, 2, 13, 5, 0, 0, tzinfo=timezone.utc)
        display_data = self.service.get_for_display(now=test_now)

        self.assertEqual(display_data["temperature"], "7.1")
        self.assertEqual(display_data["daily_low"], "N/A")
        self.assertEqual(display_data["daily_high"], "N/A")

    def test_display_matches_aware_utc_now(self):
        """An aware UTC 'now' matches the naive UTC timestamps in the forecast."""
        self.service.create(self.api_data)
        test_now = datetime(2025, 2, 13, 5, 0, 0, tzinfo=timezone.utc)
        display_data = self.service.get_for_display(now=test_now)

        self.assertEqual(display_data["temperature"], "7.1")
        self.assertEqual(display_data["daily_low"], "-5.3")
        self.assertEqual(display_data["daily_high"], "14.4")

    def test_cache_key_is_versioned(self):
        """Weather data is stored under 'weather:v2' and never under 'weather'.

        The key is versioned because the cached value is a pickled Forecast;
        bump the version whenever the cached model's shape changes.
        """
        from django.core.cache import cache

        self.service.create(self.api_data)

        cached_new = cache.get("weather:v2")
        cached_old = cache.get("weather")

        self.assertIsNotNone(cached_new)
        self.assertIsNone(cached_old)

        self.service.delete()
        self.assertIsNone(cache.get("weather:v2"))

    def test_parsed_forecast_survives_cache_round_trip(self):
        """A Forecast parsed from JSON survives the cache's pickle round trip."""
        forecast = self._build_forecast_fixture()
        original_hourly_len = len(forecast.hourly.temperature_2m)
        original_daily_len = len(forecast.daily.temperature_2m_max)

        self.service.create(forecast)
        retrieved = self.service.read()

        self.assertEqual(retrieved.latitude, forecast.latitude)
        self.assertEqual(retrieved.longitude, forecast.longitude)
        self.assertEqual(len(retrieved.hourly.temperature_2m), original_hourly_len)
        self.assertEqual(len(retrieved.daily.temperature_2m_max), original_daily_len)
        self.assertEqual(retrieved.hourly.temperature_2m[5], 7.1)
        self.assertEqual(retrieved.daily.temperature_2m_min[0], -5.3)

    def _build_forecast_fixture(self) -> Forecast:
        """Build a Forecast from an Open-Meteo API response body."""
        forecast_json = """{
          "latitude": 63.0,
          "longitude": -147.375,
          "elevation": 836.0,
          "generationtime_ms": 0.0921487808227539,
          "utc_offset_seconds": 0,
          "timezone": "GMT",
          "timezone_abbreviation": "GMT",
          "hourly_units": {
            "time": "iso8601",
            "temperature_2m": "°F",
            "relative_humidity_2m": "%"
          },
          "hourly": {
            "time": [
              "2025-02-13T00:00", "2025-02-13T01:00", "2025-02-13T02:00",
              "2025-02-13T03:00", "2025-02-13T04:00", "2025-02-13T05:00",
              "2025-02-13T06:00", "2025-02-13T07:00"
            ],
            "temperature_2m": [13.5, 14.4, 13.6, 11.8, 9.5, 7.1, 4.8, 2.8],
            "relative_humidity_2m": [68, 68, 68, 67, 67, 68, 69, 71]
          },
          "daily_units": {
            "time": "iso8601",
            "temperature_2m_max": "°F",
            "temperature_2m_min": "°F",
            "sunrise": "iso8601",
            "sunset": "iso8601"
          },
          "daily": {
            "time": ["2025-02-13", "2025-02-14"],
            "temperature_2m_max": [14.4, 4.5],
            "temperature_2m_min": [-5.3, -3.6],
            "sunrise": ["2025-02-13T17:43", "2025-02-14T17:40"],
            "sunset": ["2025-02-14T02:23", "2025-02-15T02:26"]
          }
        }"""
        return Forecast.from_json(forecast_json)
