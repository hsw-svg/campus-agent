import logging


def configure_logging() -> None:
    """Configure readable process-wide logs for local services and containers."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
