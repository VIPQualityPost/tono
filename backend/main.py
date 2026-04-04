"""
Entry point for tono.

Run with:
    python -m backend.main
or simply:
    python backend/main.py
from the tono/ directory.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Allow running as `python backend/main.py` from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiohttp import web
from backend.server import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

HOST = os.getenv("TONO_HOST", "127.0.0.1")
try:
    PORT = int(os.getenv("TONO_PORT", "8188"))
except ValueError:
    sys.exit("TONO_PORT must be a valid integer")


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = create_app(loop)

    log.info("=" * 60)
    log.info("  tono  -  topographical node-based image analysis")
    log.info("  Open your browser at  http://%s:%d", HOST, PORT)
    log.info("=" * 60)

    web.run_app(app, host=HOST, port=PORT, loop=loop, access_log=None)


if __name__ == "__main__":
    main()
