import datetime
import logging
import threading
import time

from prometheus_client import Counter, Gauge

from . import pages
from .utility import df_manipulation as util
from .utility.data_store import DataStore

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 60 * 60

last_success = Gauge(
    "dashi_data_refresh_last_success_timestamp_seconds",
    "Time when the report was last checked or updated successfully",
    ["report"],
)
duration = Gauge(
    "dashi_data_refresh_duration_seconds",
    "How long the last data refresh that rebuilt reports took",
)
failing = Gauge(
    "dashi_data_refresh_failing",
    "1 if the report's latest refresh failed and it is showing previous data, otherwise 0",
    ["report"],
)
failures = Counter(
    "dashi_data_refresh_failures",
    "Report refreshes that failed",
    ["report", "reason"],
)


def _version(page):
    caches = getattr(page, "CACHES", None)
    return util.cache_versions(caches) if caches else None


status = DataStore()
status.set({
    page.page_name: {"version": _version(page), "updated": datetime.datetime.now(), "failed": False}
    for page in pages.pages
})
for page in pages.pages:
    last_success.labels(report=page.page_name).set_to_current_time()
    failing.labels(report=page.page_name).set(0)


def status_text(name):
    current = status.get().get(name)
    if current is None:
        return ""
    text = "last updated " + current["updated"].strftime("%Y-%m-%d %H:%M")
    if current["failed"]:
        text += " (latest update failed, showing previous data)"
    return text


def updated_at(name):
    current = status.get().get(name)
    return current["updated"].isoformat() if current else None


def _ok(name, version=None):
    statuses = dict(status.get())
    current = dict(statuses[name], failed=False)
    if version is not None:
        current.update(version=version, updated=datetime.datetime.now())
    statuses[name] = current
    status.set(statuses)
    failing.labels(report=name).set(0)
    last_success.labels(report=name).set_to_current_time()


def _fail(name, reason):
    statuses = dict(status.get())
    statuses[name] = dict(statuses[name], failed=True)
    status.set(statuses)
    failing.labels(report=name).set(1)
    failures.labels(report=name, reason=reason).inc()


def refresh_all():
    start = time.monotonic()
    logger.info("Data refresh started")

    changed = []
    for page in pages.pages:
        name = page.page_name
        if getattr(page, "build", None) is None or getattr(page, "CACHES", None) is None:
            logger.critical("%s can't be refreshed: it failed to load at startup or has no build()/CACHES", name)
            _fail(name, "not_loaded")
            continue
        try:
            version = _version(page)
        except Exception:
            logger.exception("%s cache version could not be read", name)
            _fail(name, "version")
            continue
        if version == status.get()[name]["version"]:
            _ok(name)
        else:
            changed.append((page, version))

    if not changed:
        logger.info("Data refresh finished: no cache changes")
        return

    try:
        util.set_pinery(util.build_pinery())
    except Exception:
        logger.exception("Pinery failed to load, keeping previous data")
        for page, _ in changed:
            _fail(page.page_name, "pinery")
        return

    for page, version in changed:
        try:
            data = page.build()
        except Exception:
            logger.exception("%s failed to load, keeping previous data", page.page_name)
            _fail(page.page_name, "report")
            continue
        page.store.set(data)
        _ok(page.page_name, version)
        logger.info("%s updated", page.page_name)

    took = time.monotonic() - start
    duration.set(took)
    logger.info("Data refresh finished in %.1fs", took)


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
