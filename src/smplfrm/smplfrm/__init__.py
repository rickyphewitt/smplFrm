from .celery import app as celery_app
from . import views

__all__ = "celery_app"
