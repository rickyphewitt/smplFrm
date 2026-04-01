"""
URL configuration for smplfrm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers

from smplfrm.views.api.v1 import images, images_metadata, config, tasks, plugins
from smplfrm.views.index_view import IndexView
from smplfrm.plugins import get_plugin_router

api_v1_router = routers.DefaultRouter(trailing_slash=False)
api_v1_router.include_root_view = False

api_v1_router.register(r"images", images.Images, basename="images")
api_v1_router.register(
    r"images_metadata", images_metadata.ImagesMetadata, basename="images_metadata"
)
api_v1_router.register(r"configs", config.ConfigViewSet, basename="configs")
api_v1_router.register(r"tasks", tasks.TaskViewSet, basename="tasks")
api_v1_router.register(r"plugins", plugins.PluginViewSet, basename="plugins")

api_v1_plugins_router = get_plugin_router()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/plugins/", include(api_v1_plugins_router.urls)),
    path("api/v1/", include(api_v1_router.urls)),
    path("", IndexView.as_view()),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
