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

# For AWS Elastic Beanstalk, the application needs to be named 'application'
# Elastic Beanstalk looks for an object named 'application' by default
application = app


# Local API runner
def run_local():
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8127, reload=True)


if __name__ == "__main__":
    run_local()
