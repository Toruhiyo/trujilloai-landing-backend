from src.app.entities.tasks.dtos import TaskDTO
from src.app.entities.tasks.resources import list_raw_tasks, update_task_data


def recover_task_results(task_id: int, raw_task: TaskDTO):
    results_route = f"masking/{task_id}/results.json"
    update_task_data(task_id, {"results": results_route}, raw_task=raw_task)


def recover_all_tasks_results():
    tasks = list_raw_tasks()
    for task in tasks:
        recover_task_results(task.id, task)
    return tasks


if __name__ == "__main__":
    recover_all_tasks_results()
