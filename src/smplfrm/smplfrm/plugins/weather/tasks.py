import asyncio

from celery import shared_task


@shared_task(name="refresh_weather")
def refresh_weather(**kwargs):
    from smplfrm.plugins.weather.weather import WeatherPlugin

    plugin = WeatherPlugin()
    plugin.configure()
    asyncio.run(plugin.collect_weather())
