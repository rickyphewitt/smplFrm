"""Tests for weather display data formatting."""

import json
import pickle
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

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

    def test_quarter_hour_sample_is_selected(self):
        """The 15-minute sample for the elapsed quarter hour is displayed.

        'now' is aware UTC at a non-zero minute, which is the comparison the
        selector has to survive against the naive UTC forecast timestamps.
        """
        self.service.create(self._build_minutely_15_fixture([7.1, 7.4, 7.9, 8.2]))

        test_now = datetime(2025, 2, 13, 5, 37, tzinfo=timezone.utc)
        display_data = self.service.get_for_display(now=test_now)

        self.assertEqual(display_data["temperature"], "7.9")
        self.assertEqual(display_data["temperature_scale"], "F")

    def test_quarter_hour_selection_floors_rather_than_rounds(self):
        """Selection floors to the quarter hour, so it never shows a future sample."""
        self.service.create(self._build_minutely_15_fixture([7.1, 7.4, 7.9, 8.2]))

        for minute, expected in ((0, "7.1"), (14, "7.1"), (15, "7.4"), (59, "8.2")):
            with self.subTest(minute=minute):
                test_now = datetime(2025, 2, 13, 5, minute, tzinfo=timezone.utc)
                display_data = self.service.get_for_display(now=test_now)
                self.assertEqual(display_data["temperature"], expected)

    @patch("smplfrm.plugins.weather.weather.OpenMeteo")
    def test_display_needs_no_network_or_database(self, mock_open_meteo_class):
        """Display reads the cache only: no Open-Meteo call, no queries."""
        mock_open_meteo_class.side_effect = AssertionError(
            "get_for_display must not contact Open-Meteo"
        )
        self.service.create(self._build_minutely_15_fixture([7.1, 7.4, 7.9, 8.2]))

        test_now = datetime(2025, 2, 13, 5, 37, tzinfo=timezone.utc)
        with self.assertNumQueries(0):
            display_data = self.service.get_for_display(now=test_now)

        self.assertEqual(display_data["temperature"], "7.9")

    def test_null_quarter_hour_sample_falls_back_to_hourly(self):
        """A null 15-minute sample falls back to the hourly value for that hour."""
        self.service.create(self._build_minutely_15_fixture([None, None, None, None]))

        test_now = datetime(2025, 2, 13, 5, 30, tzinfo=timezone.utc)
        display_data = self.service.get_for_display(now=test_now)

        self.assertEqual(display_data["temperature"], "7.1")

    def test_null_quarter_hour_and_hourly_samples_display_na(self):
        """With both samples null the temperature is 'N/A' and the scale survives."""
        hourly_temps = [13.5, 14.4, 13.6, 11.8, 9.5, None, 4.8, 2.8]
        self.service.create(
            self._build_minutely_15_fixture([None, None, None, None], hourly_temps)
        )

        test_now = datetime(2025, 2, 13, 5, 30, tzinfo=timezone.utc)
        display_data = self.service.get_for_display(now=test_now)

        self.assertEqual(display_data["temperature"], "N/A")
        self.assertEqual(display_data["temperature_scale"], "F")

    def test_uncovered_quarter_hour_falls_back_to_hourly(self):
        """When the 15-minute series stops short of now, the hourly value is used."""
        self.service.create(self._build_minutely_15_fixture([7.1, 7.4, 7.9, 8.2]))

        test_now = datetime(2025, 2, 13, 7, 30, tzinfo=timezone.utc)
        display_data = self.service.get_for_display(now=test_now)

        self.assertEqual(display_data["temperature"], "2.8")

    def test_missing_minutely_15_series_is_not_an_error(self):
        """Falling back to hourly is a supported path and logs no error.

        A forecast without a 15-minute series is what a value cached before the
        upgrade looks like, and it stays that way until the next refresh.
        Logging it as an error would emit a line on every display request.
        """
        self.service.create(self.api_data)

        test_now = datetime(2025, 2, 13, 5, 37, tzinfo=timezone.utc)
        with self.assertNoLogs("smplfrm.plugins.weather.weather", level="ERROR"):
            display_data = self.service.get_for_display(now=test_now)

        self.assertEqual(display_data["temperature"], "7.1")

    def test_cached_series_advances_across_days_without_a_refresh(self):
        """A multi-day cached series keeps advancing through an upstream outage."""
        forecast = self._build_multi_day_fixture(days=3)
        self.service.create(forecast)

        temperatures = [
            self.service.get_for_display(
                now=datetime(2025, 2, 13, 5, 37, tzinfo=timezone.utc)
                + timedelta(days=offset)
            )["temperature"]
            for offset in range(3)
        ]

        self.assertEqual(temperatures, ["2.2", "11.8", "21.4"])
        self.assertEqual(len(set(temperatures)), 3)

    def test_minutely_15_series_survives_cache_round_trip(self):
        """The 15-minute series round-trips through the cache under 'weather:v2'."""
        from django.core.cache import cache

        forecast = self._build_multi_day_fixture(days=7)
        original_minutely_15_len = len(forecast.minutely_15.temperature_2m)

        self.service.create(forecast)
        retrieved = self.service.read()

        self.assertIsNotNone(cache.get("weather:v2"))
        self.assertIsNone(cache.get("weather"))
        self.assertIsNone(cache.get("weather:v3"))
        self.assertEqual(
            len(retrieved.minutely_15.temperature_2m), original_minutely_15_len
        )
        self.assertEqual(
            retrieved.minutely_15.temperature_2m[0],
            forecast.minutely_15.temperature_2m[0],
        )

    def test_cached_forecast_stays_small_with_minutely_15(self):
        """A 7-day forecast carrying a 15-minute series stays under 512 KB pickled."""
        forecast = self._build_multi_day_fixture(days=7)

        self.assertLess(len(pickle.dumps(forecast)), 512 * 1024)

    def _build_multi_day_fixture(self, days: int) -> Forecast:
        """Build a Forecast whose 15-minute and hourly series span whole days.

        Every sample carries a distinct value so a selected temperature
        identifies the timestamp it came from.
        """
        start = datetime(2025, 2, 13)
        quarter_hours = days * 24 * 4
        hours = days * 24
        body = {
            "latitude": 63.0,
            "longitude": -147.375,
            "elevation": 836.0,
            "generationtime_ms": 0.09,
            "utc_offset_seconds": 0,
            "timezone": "GMT",
            "timezone_abbreviation": "GMT",
            "minutely_15_units": {"time": "iso8601", "temperature_2m": "°F"},
            "minutely_15": {
                "time": [
                    (start + timedelta(minutes=15 * i)).strftime("%Y-%m-%dT%H:%M")
                    for i in range(quarter_hours)
                ],
                "temperature_2m": [round(i * 0.1, 1) for i in range(quarter_hours)],
            },
            "hourly_units": {"time": "iso8601", "temperature_2m": "°F"},
            "hourly": {
                "time": [
                    (start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M")
                    for i in range(hours)
                ],
                "temperature_2m": [round(1000 + i * 0.5, 1) for i in range(hours)],
            },
            "daily_units": {
                "time": "iso8601",
                "temperature_2m_max": "°F",
                "temperature_2m_min": "°F",
            },
            "daily": {
                "time": [
                    (start + timedelta(days=i)).strftime("%Y-%m-%d")
                    for i in range(days)
                ],
                "temperature_2m_max": [14.4] * days,
                "temperature_2m_min": [-5.3] * days,
            },
        }
        return Forecast.from_json(json.dumps(body))

    def _build_minutely_15_fixture(
        self, minutely_15_temps: list, hourly_temps: list | None = None
    ) -> Forecast:
        """Build a Forecast whose minutely_15 section covers 05:00 through 05:45.

        The hourly and daily sections mirror _build_forecast_fixture() so the
        fallback paths can be exercised against the same values.
        """
        if hourly_temps is None:
            hourly_temps = [13.5, 14.4, 13.6, 11.8, 9.5, 7.1, 4.8, 2.8]
        body = {
            "latitude": 63.0,
            "longitude": -147.375,
            "elevation": 836.0,
            "generationtime_ms": 0.09,
            "utc_offset_seconds": 0,
            "timezone": "GMT",
            "timezone_abbreviation": "GMT",
            "minutely_15_units": {"time": "iso8601", "temperature_2m": "°F"},
            "minutely_15": {
                "time": [
                    "2025-02-13T05:00",
                    "2025-02-13T05:15",
                    "2025-02-13T05:30",
                    "2025-02-13T05:45",
                ],
                "temperature_2m": minutely_15_temps,
            },
            "hourly_units": {"time": "iso8601", "temperature_2m": "°F"},
            "hourly": {
                "time": [f"2025-02-13T{hour:02d}:00" for hour in range(8)],
                "temperature_2m": hourly_temps,
            },
            "daily_units": {
                "time": "iso8601",
                "temperature_2m_max": "°F",
                "temperature_2m_min": "°F",
            },
            "daily": {
                "time": ["2025-02-13", "2025-02-14"],
                "temperature_2m_max": [14.4, 4.5],
                "temperature_2m_min": [-5.3, -3.6],
            },
        }
        return Forecast.from_json(json.dumps(body))

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
