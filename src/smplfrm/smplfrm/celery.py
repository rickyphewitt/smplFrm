import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smplfrm.settings")
app = Celery("smplfrm")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.beat_schedule = {
    "hourly-weather": {
        "task": "refresh_weather",
        "schedule": 1800
    }
}
app.autodiscover_tasks()

