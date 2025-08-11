import logging
import sys


def configure_logger():
    if "gunicorn" in sys.modules:
        # When running with Gunicorn
        gunicorn_logger = logging.getLogger("gunicorn.error")
        logger = logging.getLogger("my_app")
        logging.getLogger("logger").setLevel(logging.WARNING)
        logger.handlers = gunicorn_logger.handlers  # Use Gunicorn handlers
        logger.setLevel(logging.INFO)  # Use Gunicorn log level
    else:
        # For local development or when running without Gunicorn
        logging.getLogger("logger").setLevel(logging.WARNING)
        logging.basicConfig(
            level=logging.INFO,  # Set to INFO or WARNING in production
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),  # Logs to console
                logging.FileHandler("app.log", mode="a"),  # Logs to file
            ],
        )
        logger = logging.getLogger("my_app")
    return logger


# Create and export the logger
logger = configure_logger()
