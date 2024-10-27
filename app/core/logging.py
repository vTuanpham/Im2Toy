import logging
from pathlib import Path


def setup_logging(log_path: Path = None) -> logging.Logger:
    if log_path is None:
        log_path = Path("logs/toy_transformer.log")

    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("toy_transformer")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
