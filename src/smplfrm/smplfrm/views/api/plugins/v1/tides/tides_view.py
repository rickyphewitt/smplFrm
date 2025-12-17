from rest_framework import viewsets
from rest_framework.decorators import action

from smplfrm.plugins import TidesPlugin
import json
from django.http import HttpResponse


class TidesView(viewsets.ViewSet):

    def list(self, *args, **kwargs):
        tides = TidesPlugin().get_for_display()
        if tides:
            return HttpResponse(json.dumps(tides), content_type="application/json")
        else:
            return HttpResponse(json.dumps({}), content_type="application/json")
