import os

class Settings(object):

    def __init__(self):
        self.env_prefix = "SMPL_FRM"


    def get(self, setting_name: str, default_val):
        return os.environ.get(f"{self.env_prefix}_{setting_name}", default_val)

    def get_list(self, setting_name: str, default_val):
        csv_env_var = os.environ.get(f"{self.env_prefix}_{setting_name}", default_val)
        return csv_env_var.split(",")


settings = Settings()
root_path = os.path.dirname(os.path.realpath(__file__))

# Start config


TEMPLATE_DIRECTORIES = settings.get_list("TEMPLATE_DIRECTORIES", f"{root_path}/templates")
ASSET_DIRECTORIES = settings.get_list("ASSET_DIRECTORIES", f"{root_path}/assets")
IMAGE_REFRESH_INTERVAL = settings.get("IMAGE_REFRESH_INTERVAL", 30000)


# list of vars to render in templates
TEMPLATE_VARS = {"IMAGE_REFRESH_INTERVAL": IMAGE_REFRESH_INTERVAL}