from django.views.generic import TemplateView

from smplfrm.settings import SMPL_FRM_EXTERNAL_PORT, SMPL_FRM_HOST, SMPL_FRM_IMAGE_REFRESH_INTERVAL
class IndexView(TemplateView):
    template_name = "index.html"



    def get_context_data(self, **kwargs):
        """
        Sets the variables in the template
        :param kwargs:
        :return:
        """

        context = {
            "host": SMPL_FRM_HOST,
            "port": SMPL_FRM_EXTERNAL_PORT,
            "refresh_interval": SMPL_FRM_IMAGE_REFRESH_INTERVAL
        }

        return context



