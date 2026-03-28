import os
from celery import Celery

from smplfrm.plugins import get_beat_schedules, get_plugin_task_modules

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smplfrm.settings")
app = Celery("smplfrm")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.beat_schedule = {
    "clear-old-tasks": {"task": "clear_old_tasks", "schedule": 86400},
    **get_beat_schedules(),
}
app.autodiscover_tasks(["smplfrm.tasks"] + get_plugin_task_modules())
