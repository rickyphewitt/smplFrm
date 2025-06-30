
from rest_framework import viewsets
from rest_framework.decorators import action
from smplfrm.plugins import SpotifyPlugin
from smplfrm.settings import SMPL_FRM_EXTERNAL_PORT, SMPL_FRM_HOST, SMPL_FRM_PROTOCOL

import json
from django.http import HttpResponse
from django.shortcuts import redirect


class SpotifyView(viewsets.ViewSet):

    @action(methods=['get'], detail=False, url_path='auth')
    def auth(self, *args, **kwargs):
        auth_url = SpotifyPlugin().auth()
        return HttpResponse(json.dumps(auth_url), content_type="application/json")



    @action(methods=['get'], detail=False, url_path="now_playing")
    def get_now_playing(self, *args, **kwargs):
        """
        Get now playing song
        :param args:
        :param kwargs:
        :return:
        """
        now_playing = SpotifyPlugin().get_now_playing()
        success = now_playing.pop("success")

        if not success:
            return HttpResponse(status=412)
        return HttpResponse(json.dumps(now_playing), content_type="application/json")

    @action(methods=['get'], detail=False, url_path="callback")
    def callback(self, request, **kwargs):
        code = request.GET.get("code", "")
        response_json = SpotifyPlugin().callback(code)

        success = response_json.pop("success")
        if not success:
            return HttpResponse(status=412)
        return redirect(f"{SMPL_FRM_PROTOCOL}{SMPL_FRM_HOST}:{SMPL_FRM_EXTERNAL_PORT}")





