import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smplfrm.settings")
app = Celery("smplfrm")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()