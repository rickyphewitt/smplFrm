import settings
import os
import json
class CacheService(object):

    def __init__(self):
        # bootstrap cache directory if it doesn't exist
        if not os.path.exists(settings.CACHE_DIRECTORY):
            os.makedirs(settings.CACHE_DIRECTORY)

    def read(self, filename):
        with open(f"{settings.CACHE_DIRECTORY}/{filename}", "r") as f:
            try:
                data = json.load(f)
            except json.decoder.JSONDecodeError:
                data = {}

        return data

    def write(self, filename, json_data):
        with open(f"{settings.CACHE_DIRECTORY}/{filename}", "wt") as f:
            json.dump(json_data, f)

        return json_data
