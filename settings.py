import os

class Settings(object):

    def __init__(self):
        self.env_prefix = "SMPL_FRM"


    def get(self, setting_name: str, default_val):
        return os.environ.get(f"{self.env_prefix}_{setting_name}", default_val)



settings = Settings()
root_path = os.path.dirname(os.path.realpath(__file__))

# Start config


TEMPLATE_DIRECTORIES = settings.get("TEMPLATE_DIRECTIES", [f"{root_path}/templates"])
ASSET_DIRECTORIES = settings.get("ASSET_DIRECTORIES", [f"{root_path}/assets"])
IMAGE_REFRESH_INTERVAL = settings.get("IMAGE_REFRESH_INTERVAL", 30000)


# list of vars to render in templates
TEMPLATE_VARS = {"IMAGE_REFRESH_INTERVAL": IMAGE_REFRESH_INTERVAL}