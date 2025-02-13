from celery import signals

from smplfrm.celery import app
from smplfrm.services import LibraryService, WeatherService

@signals.worker_ready.connect
@app.task
def scan_library(**kwargs):
    LibraryService().scan()

@signals.worker_ready.connect
@app.task(name='refresh_weather')
def refresh_weather(**kwargs):
    import asyncio
    asyncio.run(WeatherService().collect_weather())
