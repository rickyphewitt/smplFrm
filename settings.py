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
LIBRARY_DIRECTORIES = settings.get_list("LIBRARY_DIRECTORIES", f"{root_path}/library")
IMAGE_REFRESH_INTERVAL = settings.get("IMAGE_REFRESH_INTERVAL", 30000)
EXTERNAL_PORT = settings.get("EXTERNAL_PORT", 8000)
HOST = settings.get("HOST", "localhost")
CACHE_DIRECTORY = settings.get("CACHE_DIRECTORY", f"{root_path}/tmp")
DISPLAY_DATE = settings.get("DISPLAY_DATE", False)
FORCE_DATE_FROM_PATH = settings.get("FORCE_DATE_FROM_PATH", True)
ALWAYS_RANDOM = settings.get("ALWAYS_RANDOM", True)
# list of vars to render in templates
TEMPLATE_VARS = {"IMAGE_REFRESH_INTERVAL": IMAGE_REFRESH_INTERVAL, "EXTERNAL_PORT": EXTERNAL_PORT, "HOST": HOST}