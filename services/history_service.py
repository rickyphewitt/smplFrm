import collections
from datetime import datetime

import settings
import os
import json

class HistoryService(object):

    def __init__(self):
        self.history_filename = ".history.json"
        self.history = {}
        if not os.path.exists(settings.CACHE_DIRECTORY):
            os.makedirs(settings.CACHE_DIRECTORY)
            with open(f"{settings.CACHE_DIRECTORY}/{self.history_filename}", "wt") as f:
                json.dump(self.history, f)


    def add(self, filename: str):
        if not self.history:
            with open(f"{settings.CACHE_DIRECTORY}/{self.history_filename}", "r") as f:
                try:
                    self.history = json.load(f)
                except json.decoder.JSONDecodeError:
                    self.history = {}


        # check to see if file exists in the history file
        if "0" in self.history and self.history.get("0") is filename:
            # @ToDo create a custom exception that more
            # accurately describes the issue
            raise Exception()
        else:
            self.history = {"0": filename}
            with open(f"{settings.CACHE_DIRECTORY}/{self.history_filename}", "wt") as f:
                json.dump(self.history, f)

    def clean(self):
        with open(f"{settings.CACHE_DIRECTORY}/{self.history_filename}", "wt") as f:
            json.dump(self.history, f)







