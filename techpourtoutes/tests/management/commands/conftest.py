import logging

import pytest

COMMAND_LOGGER = "techpourtoutes.management"


@pytest.fixture
def command_logs(caplog):
    """`caplog` only listens on the root logger, and ours does not propagate to it.

    Keeping `propagate: False` is deliberate — Sentry patches `Logger.callHandlers`, which
    runs on the originating logger, so it sees the record either way.
    """
    logger = logging.getLogger(COMMAND_LOGGER)
    logger.addHandler(caplog.handler)
    yield caplog
    logger.removeHandler(caplog.handler)
