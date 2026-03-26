from smplfrm.plugins.spotify.spotify import SpotifyPlugin
from smplfrm.plugins.weather.weather import WeatherPlugin

PLUGIN_REGISTRY = [SpotifyPlugin, WeatherPlugin]


def get_all_plugins():
    return [cls() for cls in PLUGIN_REGISTRY]


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
