import os
from celery import Celery, signals

from smplfrm.plugins import (
    get_beat_schedules,
    get_plugin_task_modules,
    get_startup_tasks,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smplfrm.settings")
app = Celery("smplfrm")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.beat_schedule = {
    "clear-old-tasks": {"task": "clear_old_tasks", "schedule": 86400},
    **get_beat_schedules(),
}
app.autodiscover_tasks(["smplfrm.tasks"] + get_plugin_task_modules())


@signals.worker_ready.connect
def run_startup_tasks(sender, **kwargs):
    for task_name in get_startup_tasks():
        app.send_task(task_name)
