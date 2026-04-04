from smplfrm.plugins.spotify.spotify import SpotifyPlugin
from smplfrm.plugins.weather.weather import WeatherPlugin

PLUGIN_REGISTRY = [SpotifyPlugin, WeatherPlugin]


def get_all_plugins():
    return [cls() for cls in PLUGIN_REGISTRY]


def get_plugin_map():
    return {plugin.name: plugin for plugin in get_all_plugins()}


def get_beat_schedules():
    schedules = {}
    for plugin in get_all_plugins():
        schedules.update(plugin.get_beat_schedule())
    return schedules


def get_plugin_task_modules():
    modules = []
    for plugin in get_all_plugins():
        if plugin.get_tasks():
            modules.append(f"smplfrm.plugins.{plugin.name}")
    return modules


def get_startup_tasks():
    tasks = {}
    for plugin in get_all_plugins():
        tasks.update(plugin.get_startup_tasks())
    return tasks


def get_plugin_router():
    from rest_framework import routers

    router = routers.DefaultRouter(trailing_slash=False)
    router.include_root_view = False
    for plugin in get_all_plugins():
        viewset = plugin.get_viewset()
        if viewset:
            router.register(plugin.get_route_prefix(), viewset, basename=plugin.name)
    return router
