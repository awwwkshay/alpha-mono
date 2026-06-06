from __future__ import annotations

import logging
import sys

from personal_agent.app import APP

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
_APP_LOGGERS = ("clay_core", "clay_app", "clay_chat", "personal_agent")
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.access", "uvicorn.error")

for _name in (*_APP_LOGGERS, *_UVICORN_LOGGERS):
    _log = logging.getLogger(_name)
    _log.setLevel(logging.DEBUG if _name in _APP_LOGGERS else logging.INFO)
    _log.handlers = [_handler]
    _log.propagate = False


def run() -> None:
    APP.serve()
