import os

class Settings(object):

    def __init__(self):
        self.env_prefix = "SMPL_FRM"


    def get(self, setting_name: str, default_val):
        return os.environ.get(f"{self.env_prefix}_{setting_name}", default_val)



settings = Settings()
root_path = os.path.dirname(os.path.realpath(__file__))
# Start config

IMAGE_TEMPLATE = settings.get("IMAGE_TEMPLATE", f"{root_path}/templates/image.html")
ASSET_DIRECTORIES = settings.get("ASSET_DIRECTORIES", [f"{root_path}/assets"])