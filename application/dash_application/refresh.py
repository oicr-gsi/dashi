import datetime
import logging
import threading
import time

from prometheus_client import Counter, Gauge

from . import pages
from .utility import df_manipulation as util
from .utility.data_store import DataStore, set_all

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 60 * 60 # 1 hour

last_success = Gauge(
    "dashi_data_refresh_last_success_timestamp_seconds",
    "Time when Dashi last loaded new data successfully",
)
duration = Gauge(
    "dashi_data_refresh_duration_seconds",
    "How long the last successful data refresh took",
)
failing = Gauge(
    "dashi_data_refresh_failing",
    "1 if the latest data refresh failed and Dashi is showing previous data, otherwise 0",
)
failures = Counter(
    "dashi_data_refresh_failures",
    "Data refreshes skipped because data failed to load",
    ["reason"],
)

status = DataStore()
status.set({"updated": datetime.datetime.now(), "failed": False})
last_success.set_to_current_time()
failing.set(0)


def status_text():
    current = status.get()
    text = "last updated " + current["updated"].strftime("%Y-%m-%d %H:%M")
    if current["failed"]:
        text += " (latest update failed, showing previous data)"
    return text


def _skip(reason, detail):
    logger.error("Data refresh skipped, keeping previous data: %s", detail)
    status.set({"updated": status.get()["updated"], "failed": True})
    failures.labels(reason=reason).inc()
    failing.set(1)


def refresh_all():
    start = time.monotonic()
    logger.info("Data refresh started")

    missing = util.missing_sources()
    if missing:
        _skip("missing_source", "missing " + ", ".join(missing))
        return

    try:
        pinery_data = util.build_pinery()
    except Exception:
        logger.exception("Pinery failed to load")
        _skip("pinery", "Pinery failed to load")
        return

    new_data = []
    with util.staged_pinery(pinery_data):
        for page in pages.pages:
            build = getattr(page, "build", None)
            if build is None:
                continue
            try:
                new_data.append((page.store, build()))
            except Exception:
                logger.exception("%s failed to load", page.page_name)
                _skip("report", page.page_name + " failed to load")
                return

    set_all(
        [(util.pinery_store, pinery_data)]
        + new_data
        + [(status, {"updated": datetime.datetime.now(), "failed": False})]
    )
    last_success.set_to_current_time()
    duration.set(time.monotonic() - start)
    failing.set(0)
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
