from django.views.generic import TemplateView

from smplfrm.settings import SMPL_FRM_EXTERNAL_PORT, SMPL_FRM_HOST, SMPL_FRM_IMAGE_REFRESH_INTERVAL, SMPL_FRM_PROTOCOL, SMPL_FRM_DISPLAY_DATE, SMPL_FRM_DISPLAY_CLOCK
class IndexView(TemplateView):
    template_name = "index.html"



    def get_context_data(self, **kwargs):
        """
        Sets the variables in the template
        :param kwargs:
        :return:
        """

        context = {
            "host": f"{SMPL_FRM_PROTOCOL}{SMPL_FRM_HOST}",
            "port": SMPL_FRM_EXTERNAL_PORT,
            "refresh_interval": SMPL_FRM_IMAGE_REFRESH_INTERVAL,
            "display_date": str(SMPL_FRM_DISPLAY_DATE).lower(),
            "display_clock": str(SMPL_FRM_DISPLAY_CLOCK).lower()
        }

        return context



