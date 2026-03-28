class BasePlugin:
    """Base class for all smplFrm plugins."""

    def __init__(self, name: str, description: str, settings: dict = None):
        self.name = name
        self.description = description
        self.settings = settings if settings is not None else {}

    def get_tasks(self) -> dict:
        """Return {task_name: task_function} for this plugin."""
        return {}

    def get_beat_schedule(self) -> dict:
        """Return Celery beat schedule entries for this plugin."""
        return {}
