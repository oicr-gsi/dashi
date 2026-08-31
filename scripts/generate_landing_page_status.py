#!/usr/bin/env python3
"""
Example script: generate the two JSON files Dashi's landing page
(`/`, `/index`, `/runs` in routes.py) reads on startup:

  - grouped_run_status.json
  - grouped_project_status.json

"Completed" here means the run-lane-sample's QC status in Pinery is
Ready or Failed (i.e. QC has been finalized, either way). "Not Ready"
(or no status recorded at all) means it's still pending. This does NOT
look at any qc-etl cache -- QC status comes straight from Pinery's
/sequencerruns endpoint.

Which page(s) a library counts towards is controlled by
--library-design-to-page, which maps Pinery library design codes
(geo_library_source_template_type) to a page name. Repeat the flag to
configure multiple pages; repeat a code across flags to route a library
to more than one page. A library whose code isn't listed in any flag
isn't counted on any page. If no --library-design-to-page flags are
passed at all, DEFAULT_LIBRARY_DESIGN_TO_PAGE below is used -- passing
even one flag replaces the defaults entirely rather than adding to them.

Reads the same QC_ETL_ROOT_DIRECTORY / PINERY_URL / PINERY_USERNAME /
PINERY_PASSWORD environment variables Dashi itself uses (from .env or the
environment). QC_ETL_ROOT_DIRECTORY is only used here to know where to
write the two JSON files (their root directory) -- this script no longer
reads any qc-etl cache, so it doesn't need the qcetl package installed.
Run this on a schedule (cron, systemd timer, etc.) to keep the landing
page reasonably up to date as new data lands.

Usage:
    uv run python scripts/generate_landing_page_status.py

    # or, to override DEFAULT_LIBRARY_DESIGN_TO_PAGE for this run only:
    uv run python scripts/generate_landing_page_status.py \\
        --library-design-to-page "WG:call-ready-wgs-ica" \\
        --library-design-to-page "WG,WGS:single-lane-wgs" \\
        --library-design-to-page "TAR,TS,TARGETED_SEQUENCING:single-lane-tar"
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

# Pinery's sample-provenance field holding a library's design code, e.g.
# "WG", "WGS", "TAR", "TS".
LIBRARY_DESIGN_COLUMN = "geo_library_source_template_type"

DEFAULT_LIBRARY_DESIGN_TO_PAGE = [
    "WG:call-ready-wgs-ica",
    # "WG,WGS:single-lane-wgs",
    # "TAR,TS,TARGETED_SEQUENCING:single-lane-tar",
]

QCED_STATES = {"Ready", "Failed"}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--library-design-to-page",
        action="append",
        metavar="CODES:PAGE_NAME",
        help=(
            "Comma-separated library design codes mapped to a landing "
            "page name, e.g. 'WG,WGS:single-lane-wgs'. Repeatable. "
            "Passing any of these replaces the built-in defaults "
            f"entirely (default: {DEFAULT_LIBRARY_DESIGN_TO_PAGE})."
        ),
    )
    return parser.parse_args()


def parse_library_design_to_page(values):
    """
    Turns repeated --library-design-to-page "CODE1,CODE2:page-name" values
    into {design_code: [page_name, ...]}.
    """
    design_code_to_pages = defaultdict(list)
    for value in values or []:
        codes_part, _, page_name = value.partition(":")
        if not page_name:
            sys.exit(
                "Invalid --library-design-to-page value (expected "
                f"CODES:PAGE_NAME): {value!r}"
            )
        for code in codes_part.split(","):
            code = code.strip()
            if code:
                design_code_to_pages[code].append(page_name)
    return design_code_to_pages


def load_qced_pinery_lims_ids(pinery_url, username=None, password=None):
    """
    Every sampleProvenanceId whose run-lane-sample QC status in Pinery is
    Ready or Failed. IDs are built the same way Pinery constructs
    sampleProvenanceId: "{sequencer_run_id}_{lane_number}_{sample_id}".
    """
    auth = (username, password) if username and password else None
    url = pinery_url.rstrip("/") + "/sequencerruns"
    response = requests.get(url, auth=auth)
    response.raise_for_status()
    sequencer_runs = response.json()

    qced_ids = set()
    for sequencer_run in sequencer_runs:
        sequencer_run_id = sequencer_run["id"]
        for container in sequencer_run.get("containers", []):
            for position in container.get("positions", []):
                lane_number = position["position"]
                for sample in position.get("samples", []):
                    status = sample.get("status", {"state": "Not Ready"})
                    if status.get("state") in QCED_STATES:
                        sample_id = f"{sequencer_run_id}_{lane_number}_{sample['id']}"
                        qced_ids.add(sample_id)
    return qced_ids


def load_pinery_sample_provenance(pinery_url, username=None, password=None):
    """
    The full set of run-libraries Pinery knows about -- this is the
    "expected" universe of libraries a run-library should show up in, used
    to figure out what's still processing (present here, absent from the
    qced set above).
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


def _get_library_design_codes(record):
    """
    LIBRARY_DESIGN_COLUMN lives under sampleAttributes (not the record's
    top level), and Pinery reports it as a single-item list, e.g. ["WG"].
    """
    value = record.get("sampleAttributes", {}).get(LIBRARY_DESIGN_COLUMN)
    if not value:
        return []
    return value if isinstance(value, list) else [value]


def _extract_aliquot_id(sample_provenance_id):
    """
    sampleProvenanceId is "{sequencer_run_id}_{lane_number}_{sample_id}",
    where sample_id is a MISO alias like "LDI8904" -- the trailing digits
    are the library aliquot's numeric MISO id (e.g. 8904), which is what
    https://miso.gsi.oicr.on.ca/libraryaliquot/<id> expects.
    """
    match = re.search(r"(\d+)$", sample_provenance_id or "")
    return match.group(1) if match else ""


def build_status(qced_ids, provenance_records, design_code_to_pages):
    """
    Groups Pinery's sample-provenance records by run and by project, and
    figures out completed vs. still-processing libraries in each group, per
    page -- a library only counts towards the page(s) design_code_to_pages
    maps its library design code to.
    """
    def new_bucket():
        return {"pages": defaultdict(lambda: {"libraries": set(), "processing": {}}), "last_modified_ms": 0}

    runs = defaultdict(new_bucket)
    projects = defaultdict(new_bucket)

    for record in provenance_records:
        sample_provenance_id = record.get("sampleProvenanceId")
        if not sample_provenance_id:
            continue

        page_names = set()
        for design_code in _get_library_design_codes(record):
            page_names.update(design_code_to_pages.get(design_code, []))
        if not page_names:
            continue

        run_name = record.get("sequencerRunName") or "unknown-run"
        project_name = record.get("studyTitle") or "unknown-project"
        library_name = record.get("sampleName") or sample_provenance_id
        aliquot_id = _extract_aliquot_id(sample_provenance_id)
        is_processing = sample_provenance_id not in qced_ids

        for bucket, key in ((runs, run_name), (projects, project_name)):
            for page_name in page_names:
                page = bucket[key]["pages"][page_name]
                page["libraries"].add(library_name)
                if is_processing:
                    page["processing"][library_name] = aliquot_id

        for date_field in ("lastModified", "createdDate"):
            ts_ms = _parse_timestamp_ms(record.get(date_field, ""))
            if ts_ms is not None:
                runs[run_name]["last_modified_ms"] = max(
                    runs[run_name]["last_modified_ms"], ts_ms
                )

    def to_entries(buckets, key_field):
        entries = []
        for name, info in buckets.items():
            pages = {
                page_name: {
                    "completed": len(page["libraries"]) - len(page["processing"]),
                    "processing": len(page["processing"]),
                    "processing_libraries": sorted(
                        f"{lib_name}:{aliquot_id}"
                        for lib_name, aliquot_id in page["processing"].items()
                    ),
                }
                for page_name, page in info["pages"].items()
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
    args = parse_args()
    design_code_to_pages = parse_library_design_to_page(
        args.library_design_to_page or DEFAULT_LIBRARY_DESIGN_TO_PAGE
    )

    qc_etl_root_directory = os.getenv("QC_ETL_ROOT_DIRECTORY")
    if not qc_etl_root_directory:
        sys.exit("QC_ETL_ROOT_DIRECTORY must be set")

    output_directory = qc_etl_root_directory.split(":")[0]

    pinery_url = os.getenv("PINERY_URL")
    if not pinery_url:
        sys.exit("PINERY_URL must be set")

    pinery_username = os.getenv("PINERY_USERNAME")
    pinery_password = os.getenv("PINERY_PASSWORD")

    qced_ids = load_qced_pinery_lims_ids(pinery_url, pinery_username, pinery_password)
    provenance_records = load_pinery_sample_provenance(
        pinery_url, pinery_username, pinery_password
    )

    run_status, project_status = build_status(
        qced_ids, provenance_records, design_code_to_pages
    )

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
