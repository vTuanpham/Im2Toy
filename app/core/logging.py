import logging
from typing import Union
from pathlib import Path
from datetime import datetime, timedelta, timezone


# Set up Vietnam timezone (UTC+7)
VN_TZ = timezone(timedelta(hours=7))


def vn_time():
    """Return current time in Vietnam timezone."""
    return datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")


def setup_logging(log_path: Union[Path, None] = None) -> logging.Logger:
    if log_path is None:
        log_path = Path("logs/toy_transformer.log")

    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("toy_transformer")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    formatter.converter = lambda *args: datetime.now(VN_TZ).timetuple()

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
