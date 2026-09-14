import os
from celery import Celery, signals

from smplfrm.plugins import (
    get_plugin_task_modules,
    get_startup_tasks,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smplfrm.settings")
app = Celery("smplfrm")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["smplfrm.tasks"] + get_plugin_task_modules())


@signals.worker_init.connect
def load_preload_tasks(sender, **kwargs):
    """Import preload_tasks module to register tasks with Celery.

    This runs when worker initializes, after Django apps are loaded.
    preload_tasks.py is not discovered by autodiscover_tasks because
    autodiscover only scans the module root (tasks.py), not submodules.
    """
    import smplfrm.tasks.preload_tasks  # noqa: F401


@signals.worker_ready.connect
def run_startup_tasks(sender, **kwargs):
    for task_name in get_startup_tasks():
        app.send_task(task_name)
