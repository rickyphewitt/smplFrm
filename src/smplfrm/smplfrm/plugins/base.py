class BasePlugin:
    """Base class for all smplFrm plugins."""

    name: str
    description: str

    def get_tasks(self) -> dict:
        """Return {task_name: task_function} for this plugin."""
        return {}

    def get_beat_schedule(self) -> dict:
        """Return Celery beat schedule entries for this plugin."""
        return {}
