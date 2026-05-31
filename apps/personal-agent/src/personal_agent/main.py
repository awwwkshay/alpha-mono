from __future__ import annotations

import logging
import sys

from personal_agent.app import APP

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
for _name in (
    "alpha_core",
    "alpha_chat",
    "personal_agent",
    "uvicorn",
    "uvicorn.access",
    "uvicorn.error",
):
    _log = logging.getLogger(_name)
    _log.setLevel(
        logging.DEBUG
        if _name not in ("uvicorn", "uvicorn.access", "uvicorn.error")
        else logging.INFO
    )
    _log.handlers = []
    _log.addHandler(_handler)
    _log.propagate = False


def run() -> None:
    APP.serve()
