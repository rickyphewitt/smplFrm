from rest_framework import viewsets
from rest_framework.decorators import action

from smplfrm.plugins import TidesPlugin


class TidesView(viewsets.ViewSet):

    @action(methods=["get"], detail=False)
    def read(self, *args, **kwargs):

        return HttpResponse(json.dumps(auth_url), content_type="application/json")
