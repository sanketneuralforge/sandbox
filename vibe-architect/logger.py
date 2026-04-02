# logger.py

import logging
from pathlib import Path

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/vibe_architect.log"),
        logging.StreamHandler(),
    ]
)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)