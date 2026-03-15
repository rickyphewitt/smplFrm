import asyncio
import logging

from celery import shared_task, signals

from smplfrm.celery import app
from smplfrm.services import (
    CacheService,
    ImageManipulationService,
    ImageService,
    LibraryService,
    WeatherService,
)
from smplfrm.services.task_service import TaskService

logger = logging.getLogger(__name__)


def _run_with_task_tracking(task_id: str, fn):
    """Run a function with Task model progress tracking.

    Args:
        task_id: External ID of the Task record, or None
        fn: Callable that accepts an optional on_progress callback
    """
    if not task_id:
        fn()
        return

    service = TaskService()
    task = service.read(task_id)
    service.start(task)
    try:

        def on_progress(pct):
            service.update_progress(task, pct)

        fn(on_progress=on_progress)
        service.complete(task)
    except Exception as e:
        service.fail(task, str(e))
        raise


@signals.worker_ready.connect
@app.task(name="scan_library")
def scan_library(task_id=None, **kwargs):
    _run_with_task_tracking(task_id, LibraryService().scan)


@signals.worker_ready.connect
@app.task(name="reset_image_count")
def reset_image_counts(task_id=None, **kwargs):
    _run_with_task_tracking(task_id, ImageService().reset_all_view_count)


@signals.worker_ready.connect
@app.task(name="refresh_weather")
def refresh_weather(**kwargs):
    asyncio.run(WeatherService().collect_weather())


@signals.worker_ready.connect
@app.task(name="clear_cache")
def clear_cache(task_id=None, **kwargs):
    _run_with_task_tracking(task_id, CacheService().clear)


def cache_images(images_ext_ids: list, height: str, width: str):
    """
    Cache images if not already cached
    :param images_ext_ids: List of image external IDs
    :param height: Target height for cached images
    :param width: Target width for cached images
    """
    if not images_ext_ids or not height or not width:
        return

    cache_service = CacheService()
    image_manipulation = ImageManipulationService()
    image_service = ImageService()

    images = image_service.list(external_id__in=images_ext_ids)

    for image in images:
        cache_key = cache_service.get_image_cache_key(image.external_id, height, width)
        cached_image = cache_service.read(cache_key=cache_key)
        if cached_image is None:
            cached_image = image_manipulation.display(image, int(height), int(width))
            cache_service.upsert(cache_key=cache_key, cache_data=cached_image)


@shared_task()
def cache_images_task(images_ext_ids=None, height=None, width=None):
    logger.info("Running Cache Images Task")
    cache_images(images_ext_ids, height, width)
