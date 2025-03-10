from src.app.common.enums import ProcessStatusType
from src.app.entities.tasks.resources import list_raw_tasks, update_task_data


def update_all_tasks(params: dict):
    tasks = list_raw_tasks()
    for task in tasks:
        update_task_data(task.id, params, raw_task=task)
    return tasks


if __name__ == "__main__":
    update_all_tasks({"status": ProcessStatusType.SUCCESS, "error": None})
