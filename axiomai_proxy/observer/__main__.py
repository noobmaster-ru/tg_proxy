from __future__ import annotations

import asyncio
import logging

from axiomai_proxy.infrastructure.di import build_container, close_container
from axiomai_proxy.infrastructure.logging import setup_logging

logger = logging.getLogger(__name__)


async def run() -> None:
    setup_logging()
    container = await build_container()
    try:
        logger.info("Observer запущен")
        while True:
            await asyncio.sleep(3600)
    finally:
        await close_container(container)


def main() -> None:
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Observer остановлен")


if __name__ == "__main__":
    main()
