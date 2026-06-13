import asyncio
import logging
import signal
import sys

from app.workers.base import WorkerBase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


WORKER_TYPES: dict[str, type[WorkerBase]] = {}


def _register():
    global WORKER_TYPES
    try:
        from app.workers.scheduler import SchedulerWorker
        WORKER_TYPES["scheduler"] = SchedulerWorker
    except ImportError:
        pass
    try:
        from app.workers.listener import ListenerWorker
        WORKER_TYPES["listener"] = ListenerWorker
    except ImportError:
        pass
    try:
        from app.workers.detail import DetailWorker
        WORKER_TYPES["detail"] = DetailWorker
    except ImportError:
        pass
    try:
        from app.workers.health import HealthWorker
        WORKER_TYPES["health"] = HealthWorker
    except ImportError:
        pass


_register()


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in WORKER_TYPES:
        print(f"Usage: python -m app.workers <{'|'.join(WORKER_TYPES.keys())}>")
        sys.exit(1)

    worker_type = sys.argv[1]
    worker_cls = WORKER_TYPES[worker_type]
    worker = worker_cls()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _shutdown(signum, frame):
        logger.info("received signal %s, shutting down", signum)
        worker.stop()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("starting %s worker", worker_type)
    loop.run_until_complete(worker.run())
    loop.close()
    logger.info("%s worker stopped", worker_type)


if __name__ == "__main__":
    main()
