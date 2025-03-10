from typing import Optional
from src.app.common.enums import ProcessStatusType
from src.app.entities.tasks.resources import list_raw_tasks, retry_task


def retry_tasks(specific_status: Optional[list[ProcessStatusType]] = None):
    tasks = list_raw_tasks()
    tasks = [
        task for task in tasks if not specific_status or task.status in specific_status
    ]
    for task in tasks:
        retry_task(task.id)
    return tasks


if __name__ == "__main__":
    retry_tasks(specific_status=[ProcessStatusType.FAILED])
