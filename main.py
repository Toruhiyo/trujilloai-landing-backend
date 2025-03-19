from mangum import Mangum
import logging

from src.app.app import app

# Set up logging
logger = logging.getLogger(__name__)
# Configure log level to ensure INFO logs are displayed
logger.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
logging.getLogger("urllib3").setLevel(logging.WARNING)


# Custom Lambda handler that logs event and context
def lambda_handler(event, context):
    logger.info(f"Lambda event: {event}")

    # Log useful context attributes
    if context:
        context_details = {
            "function_name": getattr(context, "function_name", "N/A"),
            "function_version": getattr(context, "function_version", "N/A"),
            "invoked_function_arn": getattr(context, "invoked_function_arn", "N/A"),
            "aws_request_id": getattr(context, "aws_request_id", "N/A"),
            "log_group_name": getattr(context, "log_group_name", "N/A"),
            "log_stream_name": getattr(context, "log_stream_name", "N/A"),
            "memory_limit_in_mb": getattr(context, "memory_limit_in_mb", "N/A"),
            "remaining_time_in_millis": getattr(
                context, "get_remaining_time_in_millis", lambda: "N/A"
            )(),
        }
        logger.info(f"Lambda context: {context_details}")

    # Check if this is a WebSocket event
    if "requestContext" in event and event["requestContext"].get("connectionId"):
        return handle_websocket_event(event, context)

    # Regular HTTP event - use Mangum
    mangum_handler = Mangum(app)
    return mangum_handler(event, context)


def handle_websocket_event(event, context):
    connection_id = event["requestContext"]["connectionId"]
    route_key = event["requestContext"]["routeKey"]

    if route_key == "$connect":
        # Handle connection establishment
        return {"statusCode": 200}
    elif route_key == "$disconnect":
        # Handle disconnection
        return {"statusCode": 200}
    elif route_key == "$default":
        # Handle messages - you'll need to adapt your existing WebSocket handler
        # to work with the API Gateway WebSocket format
        return {"statusCode": 200}


# Local API runner
def run_local():
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8127, reload=True)


if __name__ == "__main__":
    run_local()
