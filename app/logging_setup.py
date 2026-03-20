import logging
import logging.handlers

from app.config import Settings, _PROJECT_ROOT


def configure_logging(settings: Settings) -> None:
    log_dir = _PROJECT_ROOT / settings.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "app.log"
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",
        interval=1,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    app_logger = logging.getLogger("app")
    app_logger.handlers.clear()
    app_logger.setLevel(level)
    app_logger.addHandler(file_handler)
    app_logger.propagate = False
