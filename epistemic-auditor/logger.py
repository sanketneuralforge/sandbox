import logging
from pathlib import Path

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_LOG_DIR = Path(__file__).resolve().parent / "logs"
_LOG_FILE = _LOG_DIR / "app.log"
_configured = False


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured project logger.
    Logs go to stderr (console) and to logs/app.log under this package.
    """
    global _configured
    logger = logging.getLogger(name)

    if not _configured:
        root = logging.getLogger()
        root.setLevel(logging.INFO)

        formatter = logging.Formatter(_LOG_FORMAT)

        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)

        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

        _configured = True

    return logger
