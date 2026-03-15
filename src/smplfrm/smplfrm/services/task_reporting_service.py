import logging

from smplfrm.models.task import TaskType

logger = logging.getLogger(__name__)


class TaskReportingService:

    def __init__(self, task_type: TaskType = None):
        from smplfrm.services import TaskService

        self.task_service = TaskService()
        self.task_type = task_type
        self.total = 0
        self.task_id = None

    def initiate_task(self, task_id: str, total: int):
        task = None
        if task_id is None:
            task = self.task_service.create({"task_type": self.task_type})
            logger.info(f"Task Created: {task.external_id} for Task: {self.task_type}")
        else:
            task = self.task_service.read(task_id)

        self.task_id = task.external_id
        self.total = total
        # start the task
        self.task_service.start(task)

    def report_task(self, processed: int):
        # update progress every 5th element
        if processed % 5 == 0 or processed == self.total:
            task = self.task_service.read(self.task_id)
            task.progress = int(processed / self.total * 100)
            self.task_service.update(task)
            logger.info(
                f"Task with Id: {task.external_id} updated with progress {task.progress}%"
            )

    def complete_task(self):
        task = self.task_service.read(self.task_id)
        task.progress = 100
        self.task_service.complete(task)

    def fail_task(self, error: str):
        task = self.task_service.read(self.task_id)
        self.task_service.fail(task, error)
