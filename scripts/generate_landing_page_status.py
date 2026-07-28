#!/usr/bin/env python3
"""
Example script: generate the two JSON files Dashi's landing page
(`/`, `/index`, `/runs` in routes.py) reads on startup:

  - grouped_run_status.json
  - grouped_project_status.json

To track a NEW report on the landing page later, add another entry to
REPORT_CACHE_MAPPINGS below.

Usage:
    uv run python scripts/generate_landing_page_status.py

Reads the same QC_ETL_ROOT_DIRECTORY / PINERY_URL / PINERY_USERNAME /
PINERY_PASSWORD environment variables Dashi itself uses (from .env or the
environment), and writes both JSON files to the root of
QC_ETL_ROOT_DIRECTORY -- NOT inside any single cache's own folder. Run this
on a schedule (cron, systemd timer, etc.) to keep the landing page
reasonably up to date as new data lands.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from qcetl import QCETLMultiCache
import qcetl.column

load_dotenv()

# One entry per report tracked on the landing page: the qcetl
# cache name that backs it, and the Dashi page name (as used in the URL /
# ALL_REPORTS in pages.py) the resulting counts should be attributed to.
REPORT_CACHE_MAPPINGS = [
    {"cache_name": "icametrics", "page_name": "call-ready-wgs-ica"},
]

PINERY_LIMS_ID_COLUMN = qcetl.column.ColumnNames.PineryLimsID


def load_completed_pinery_lims_ids(qc_etl_root_directory, cache_name):
    """
    Every Pinery Lims ID that already has a row in the given qcetl cache --
    i.e. has been QC'ed for that cache's report, per this script's
    definition of "complete".
    """
    root_dirs = qc_etl_root_directory.split(":")
    cache = QCETLMultiCache(root_dirs)
    df = cache.load_same_version(cache_name).unique(cache_name)
    return set(df[PINERY_LIMS_ID_COLUMN])


def load_pinery_sample_provenance(pinery_url, username=None, password=None):
    """
    The full set of run-libraries Pinery knows about -- this is the
    "expected" universe of libraries a run-library should show up in, used
    to figure out what's still processing (present here, absent from the
    qcetl cache above).
    """
    url = pinery_url.rstrip("/") + "/provenance/latest/sample-provenance"
    auth = (username, password) if username and password else None
    response = requests.get(url, auth=auth)
    response.raise_for_status()
    return response.json()


def _parse_timestamp_ms(iso_string):
    try:
        return int(
            datetime.fromisoformat(iso_string.replace("Z", "+00:00")).timestamp()
            * 1000
        )
    except (ValueError, AttributeError):
        return None


def build_status(completed_ids_by_page, provenance_records):
    """
    Groups Pinery's sample-provenance records by run and by project, and
    figures out -- per report in REPORT_CACHE_MAPPINGS -- completed vs.
    still-processing libraries in each group.
    """
    def new_bucket():
        return {
            "libraries": set(),
            "processing": {page_name: set() for page_name in completed_ids_by_page},
            "last_modified_ms": 0,
        }

    runs = defaultdict(new_bucket)
    projects = defaultdict(new_bucket)

    for record in provenance_records:
        sample_provenance_id = record.get("sampleProvenanceId")
        if not sample_provenance_id:
            continue

        run_name = record.get("sequencerRunName") or "unknown-run"
        project_name = record.get("studyTitle") or "unknown-project"
        library_name = record.get("sampleName") or sample_provenance_id

        for bucket, key in ((runs, run_name), (projects, project_name)):
            bucket[key]["libraries"].add(library_name)
            for page_name, completed_ids in completed_ids_by_page.items():
                if sample_provenance_id not in completed_ids:
                    bucket[key]["processing"][page_name].add(library_name)

        for date_field in ("lastModified", "createdDate"):
            ts_ms = _parse_timestamp_ms(record.get(date_field, ""))
            if ts_ms is not None:
                runs[run_name]["last_modified_ms"] = max(
                    runs[run_name]["last_modified_ms"], ts_ms
                )

    def to_entries(buckets, key_field):
        entries = []
        for name, info in buckets.items():
            pages = {}
            for page_name, processing_libraries in info["processing"].items():
                completed_count = len(info["libraries"]) - len(processing_libraries)
                pages[page_name] = {
                    "completed": completed_count,
                    "processing": len(processing_libraries),
                    "processing_libraries": sorted(processing_libraries),
                }
            entry = {key_field: name, "pages": pages}
            if info["last_modified_ms"]:
                entry["run_completed"] = info["last_modified_ms"]
            elif key_field == "run":
                entry["run_completed"] = int(datetime.now(timezone.utc).timestamp() * 1000)
            entries.append(entry)
        return entries

    return to_entries(runs, "run"), to_entries(projects, "project")


def main():
    qc_etl_root_directory = os.getenv("QC_ETL_ROOT_DIRECTORY")
    if not qc_etl_root_directory:
        sys.exit("QC_ETL_ROOT_DIRECTORY must be set")

    output_directory = qc_etl_root_directory.split(":")[0]

    pinery_url = os.getenv("PINERY_URL")
    if not pinery_url:
        sys.exit("PINERY_URL must be set")

    completed_ids_by_page = {
        mapping["page_name"]: load_completed_pinery_lims_ids(
            qc_etl_root_directory, mapping["cache_name"]
        )
        for mapping in REPORT_CACHE_MAPPINGS
    }
    provenance_records = load_pinery_sample_provenance(
        pinery_url, os.getenv("PINERY_USERNAME"), os.getenv("PINERY_PASSWORD")
    )

    run_status, project_status = build_status(completed_ids_by_page, provenance_records)

    run_status_path = os.path.join(output_directory, "grouped_run_status.json")
    project_status_path = os.path.join(output_directory, "grouped_project_status.json")

    with open(run_status_path, "w") as f:
        json.dump(run_status, f, indent=2)

    with open(project_status_path, "w") as f:
        json.dump(project_status, f, indent=2)

    print(f"Wrote {len(run_status)} run(s) to {run_status_path}")
    print(f"Wrote {len(project_status)} project(s) to {project_status_path}")


if __name__ == "__main__":
    main()
