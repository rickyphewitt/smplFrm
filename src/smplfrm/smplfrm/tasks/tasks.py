from celery import shared_task, signals

from smplfrm.celery import app
from smplfrm.services import LibraryService


@signals.worker_ready.connect
@app.task
def scan_library(**kwargs):
    LibraryService().scan()