import logging
import threading
import time

from . import pages
from .utility import df_manipulation as util

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 60 * 60  # 1 hours


def refresh_all():
    start = time.monotonic()
    logger.info("Data refresh started")
    try:
        util.refresh_pinery()
    except Exception:
        logger.exception("Pinery refresh failed; keeping previous Pinery data")
    for page in pages.pages:
        refresh = getattr(page, "refresh", None)
        if refresh is None:
            continue
        try:
            refresh()
        except Exception:
            logger.exception("Refresh failed for %s; keeping previous data", page.page_name)
    logger.info("Data refresh finished in %.1fs", time.monotonic() - start)


def start_refresh_timer(interval_seconds=REFRESH_INTERVAL_SECONDS):
    def loop():
        while True:
            time.sleep(interval_seconds)
            try:
                refresh_all()
            except Exception:
                logger.exception("Data refresh failed")

    threading.Thread(target=loop, name="dashi-refresh-timer", daemon=True).start()
    logger.info("Data refresh timer started: every %d seconds", interval_seconds)
