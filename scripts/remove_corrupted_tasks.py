import logging
from src.app.entities.tasks.dtos import TaskDTO
from src.config.vars_grabber import VariablesGrabber
from src.wrappers.aws.dynamodb import DynamoDBWrapper

TASKS_DYNAMODB_TABLE_NAME = VariablesGrabber().get("TASKS_DYNAMODB_TABLE_NAME")

logger = logging.getLogger(__name__)


def remove_corrupted_tasks() -> None:
    tasks_items = DynamoDBWrapper().list_items(
        table_name=TASKS_DYNAMODB_TABLE_NAME,
        limit=None,
    )
    removed_tasks = 0
    for item in tasks_items:
        if not item.get("id"):
            logger.warning(f"Task with id {item['id']} has no id. Skipping")
            continue
        try:
            TaskDTO(**item)
        except Exception:
            DynamoDBWrapper().delete_item(
                table_name=TASKS_DYNAMODB_TABLE_NAME,
                item_key={"id": item["id"]},
            )
            logger.info(f"Task with id {item['id']} was removed")
            removed_tasks += 1
    logger.info(
        f"Removed {removed_tasks} corrupted tasks from {len(tasks_items)} tasks"
    )


if __name__ == "__main__":
    remove_corrupted_tasks()
