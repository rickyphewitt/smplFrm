from collections import OrderedDict
from datetime import datetime, timedelta
from math import trunc

import pandas as pd
import requests
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify, CacheFileHandler
from django.conf import settings
from django.core.cache import cache

import logging

logger = logging.getLogger(__name__)

from noaa_coops import Station


class TidesPlugin(object):

    def __init__(self):
        self.redis_key = "tides"
        self.station_id = settings.SMPL_FRM_PLUGINS_TIDES_STATION_ID
        self.enabled = False
        if self.station_id != "":
            self.enabled = True
            self.station = Station(self.station_id)
        else:
            logger.warning("Tides Plugin Not Enabled")

    def get_tide_data(self, begin_date: str, end_date: str):
        """
        CAlls the NOAA api to get tide data for a date range
        :param begin_date:
        :param end_date:
        :return:
        """
        try:
            return self.station.get_data(
                product="predictions",
                begin_date=begin_date,
                end_date=end_date,
                interval="hilo",
                datum="MLLW",
                units="english",
            )
        except Exception as e:
            logger.exception("Failed to get tides from NOAA")

    def parse_tide_data(self, tide_data_frame: pd.DataFrame):
        """
        Parse the tide data for a given date range
        :param tide_data_frame:
        :return:
        """
        tide_data = OrderedDict()

        if tide_data_frame is not None:
            for row in tide_data_frame.iterrows():
                tide_data[row[0]] = (row[1].type, row[1].v)

            # cache tide data for next call
            self.create(tide_data)
        else:
            logger.error("Failed to get tides from NOAA")
        return tide_data

    def create(self, data):
        expires = timedelta(days=3).total_seconds()
        cache.set(key=self.redis_key, value=data, timeout=expires)
        logger.debug("Persisted Tide Data: " + str(data))
        print("Tides Synced")

    def delete(self):
        cache.delete(self.redis_key)

    def read(self):
        return cache.get(self.redis_key)

    def get_for_display(self):
        """
        Gets the tide data from the cache, if it doesn't
        exist it will call to the NOAA api and store it
        :return:
        """
        tides = self.read()
        if tides is None:
            logger.debug("Tides not found in cache, syncing")
            dt = datetime.now()
            begin_date = dt.strftime("%Y%m%d")
            end_date = (dt + timedelta(days=7)).strftime("%Y%m%d")
            tide_data_frame = self.get_tide_data(begin_date, end_date)
            if tide_data_frame is not None:
                tides = self.parse_tide_data(tide_data_frame)

        # if we have tides format and return them
        if tides:
            # build up json object to be returned
            display_tides = {}
            for timestamp, (tide_type, height) in tides.items():
                display_tides[timestamp] = {"type": tide_type, "height": height}

            # return to be displayed in UI
            return display_tides
        else:
            return None
