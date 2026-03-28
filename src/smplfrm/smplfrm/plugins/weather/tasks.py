import asyncio

from celery import shared_task


@shared_task(name="refresh_weather")
def refresh_weather(**kwargs):
    from smplfrm.plugins.weather.weather import WeatherPlugin

    asyncio.run(WeatherPlugin().collect_weather())
