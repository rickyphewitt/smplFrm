from celery import signals
from celery import shared_task

from smplfrm.celery import app
from smplfrm.services import LibraryService, WeatherService, CacheService, ImageManipulationService, ImageService

@signals.worker_ready.connect
@app.task
def scan_library(**kwargs):
    LibraryService().scan()


@signals.worker_ready.connect
@app.task(name='reset_image_count')
def reset_image_counts(**kwargs):
    ImageService().reset_all_view_count()

@signals.worker_ready.connect
@app.task(name='refresh_weather')
def refresh_weather(**kwargs):
    import asyncio
    asyncio.run(WeatherService().collect_weather())

@signals.worker_ready.connect
@app.task(name='clear_cache')
def clear_cache(**kwargs):
    CacheService().clear()




def cache_images(images_ext_ids: list, height: str, width: str):
    """
    Cache images if not already cached
    :param images:
    :param height:
    :param width:
    :return:
    """
    if not images_ext_ids or not height or not width:
        return
    else:
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
    print("Running Cache Images Task")
    cache_images(images_ext_ids, height,width)









